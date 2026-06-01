"""
SerpApiBookingClient — resolves a booking_token into a purchasable URL.

Flow:
  1. Re-call SerpApi Google Flights with the original search params + booking_token.
  2. Parse booking_options from the response, pick the cheapest offer.
  3. POST to booking_request.url with booking_request.post_data (form-encoded).
  4. Parse the meta-refresh redirect URL from Google's HTML response.
  5. Return the final vendor booking URL.
"""

import html as _html
import re
from urllib.parse import parse_qs

import httpx

from app.modules.flights.domain.interfaces import BookingLinkProvider

_SERPAPI_BASE = "https://serpapi.com/search"


def _ssl_context() -> bool | object:
    """Return an SSL context that trusts OS certificate stores if truststore is available."""
    try:
        import ssl as _ssl
        import truststore
        ctx = truststore.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
        return ctx
    except ImportError:
        return True


def _pick_cheapest(booking_options: list[dict]) -> dict | None:
    """Return the booking_request dict for the cheapest 'together' option."""
    best: dict | None = None
    best_price: float = float("inf")

    for option in booking_options:
        together = option.get("together", {})
        price = together.get("price", float("inf"))
        if price < best_price:
            best_price = price
            best = together.get("booking_request")

    return best


def _extract_meta_refresh_url(html: str) -> str:
    """
    Extract the redirect URL from a meta-refresh tag:
      <meta content="0;url='https://...'" http-equiv="refresh">
    """
    match = re.search(
        r"""<meta[^>]+http-equiv=["\']refresh["\'][^>]*content=["\'][^"\']*url=["\']([^"\']+)["\']""",
        html,
        re.IGNORECASE,
    )
    if not match:
        # Try reversed attribute order (content before http-equiv)
        match = re.search(
            r"""<meta[^>]+content=["\'][^"\']*url=["\']([^"\']+)["\'][^>]*http-equiv=["\']refresh["\']""",
            html,
            re.IGNORECASE,
        )
    if not match:
        raise ValueError("Could not find meta-refresh URL in Google response")
    return _html.unescape(match.group(1))


class SerpApiBookingClient(BookingLinkProvider):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def fetch_booking_options(
        self,
        booking_token: str,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
    ) -> list[dict]:
        """Re-call SerpApi with booking_token to get per-vendor booking options."""
        params: dict[str, str] = {
            "engine": "google_flights",
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "type": "2",       # one-way (token carries all info anyway)
            "hl": "en",
            "gl": "us",
            "currency": "EUR",
            "booking_token": booking_token,
            "api_key": self._api_key,
        }

        async with httpx.AsyncClient(timeout=25, verify=_ssl_context()) as client:
            response = await client.get(_SERPAPI_BASE, params=params)
            response.raise_for_status()
            data = response.json()

        return data.get("booking_options", [])

    async def resolve_url(self, url: str, post_data: str) -> str:
        """
        POST post_data to url (application/x-www-form-urlencoded),
        then parse the meta-refresh redirect URL from the HTML response.

        post_data is in the form  'u=ADowPO...'  (already the query-string body).
        We parse out the 'u' value and re-encode it so httpx handles escaping.
        """
        # Parse post_data to extract the raw value of 'u'
        parsed = parse_qs(post_data, keep_blank_values=True)
        u_values = parsed.get("u", [])
        if not u_values:
            raise ValueError(f"post_data does not contain 'u' parameter: {post_data[:80]}")

        form_data = {"u": u_values[0]}

        async with httpx.AsyncClient(
            timeout=20,
            verify=_ssl_context(),
            follow_redirects=False,   # We want the raw HTML, not the final page
        ) as client:
            response = await client.post(url, data=form_data)

        html = response.text
        return _extract_meta_refresh_url(html)


class FakeBookingClient(BookingLinkProvider):
    """
    Returns a placeholder URL — used when SERPAPI_KEY is not configured.
    """

    async def fetch_booking_options(
        self,
        booking_token: str,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
    ) -> list[dict]:
        return [
            {
                "together": {
                    "book_with": "Fake Airline",
                    "price": 99,
                    "booking_request": {
                        "url": "https://example.com",
                        "post_data": "u=fake",
                    },
                }
            }
        ]

    async def resolve_url(self, url: str, post_data: str) -> str:
        return "https://example.com/fake-booking"

