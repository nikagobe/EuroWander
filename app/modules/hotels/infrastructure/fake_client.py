"""
Fake Booking.com client for local development.
Returns static results when RAPIDAPI_KEY is not configured.
"""

from datetime import date as DateType

from app.modules.hotels.domain.entities import (
    HotelDestination,
    HotelDetails,
    HotelOffer,
    HotelRoom,
    HotelRoomHighlight,
)
from app.modules.hotels.domain.interfaces import (
    HotelDestinationProvider,
    HotelDetailsProvider,
    HotelSearchProvider,
)

_FAKE_DESTINATIONS: list[dict[str, str]] = [
    {
        "dest_id": "-2167973",
        "city_name": "Lisbon",
        "label": "Lisbon, Lisbon Region, Portugal",
    },
    {
        "dest_id": "-2601889",
        "city_name": "Paris",
        "label": "Paris, Île-de-France, France",
    },
    {
        "dest_id": "-2602512",
        "city_name": "Manchester",
        "label": "Manchester, Greater Manchester, United Kingdom",
    },
    {
        "dest_id": "-372490",
        "city_name": "Barcelona",
        "label": "Barcelona, Catalonia, Spain",
    },
    {
        "dest_id": "-1746443",
        "city_name": "Berlin",
        "label": "Berlin, Germany",
    },
    {
        "dest_id": "-2601422",
        "city_name": "Rome",
        "label": "Rome, Lazio, Italy",
    },
]

_FAKE_HOTELS: list[dict] = [
    {
        "hotel_id": 9400894,
        "name": "Martinhal Lisbon Oriente",
        "latitude": 38.761582,
        "longitude": -9.098131,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/466945356.jpg?k=02b94e0b6e0af31bef98df0d76586f3f27323a259f8a781cc0b36899d23535ac&o=",
        "stars": 5,
        "review_score": 9.6,
        "review_score_word": "Exceptional",
        "review_count": 1358,
        "price": 1340.54,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "11:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 10963846,
        "name": "Haws Lisboa",
        "latitude": 38.722667677286,
        "longitude": -9.133524630688,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/508051702.jpg?k=531e9ea2eea62697767ad92aa5b598dee6e5d423d80019cf695e003f255d8326&o=",
        "stars": 4,
        "review_score": 9.6,
        "review_score_word": "Exceptional",
        "review_count": 920,
        "price": 1395.71,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 364738,
        "name": "Casa Balthazar",
        "latitude": 38.7132835992152,
        "longitude": -9.14159461855888,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/75170949.jpg?k=d0015493cdd908c08c42395c1f2d8b35f8df4d802edf4416f1d6014b85ba362f&o=",
        "stars": 4,
        "review_score": 9.7,
        "review_score_word": "Exceptional",
        "review_count": 647,
        "price": 1234.10,
        "currency": "EUR",
        "checkin_from": "14:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 1966478,
        "name": "Chiado Camões Apartments | Lisbon Best Apartments",
        "latitude": 38.7110251966628,
        "longitude": -9.14346953642348,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/506577514.jpg?k=bed6cf86fb97cdfb929aec8fde3a7cd25398409809720a4f0d805a887f0aee6e&o=",
        "stars": 4,
        "review_score": 9.5,
        "review_score_word": "Exceptional",
        "review_count": 379,
        "price": 1514.26,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 38599,
        "name": "Hotel Britania Art Deco Lisboa",
        "latitude": 38.7215699113269,
        "longitude": -9.14552673697472,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/326764141.jpg?k=b8a87716f4107f8c6ce08d85b413bb8a0345ab4654aecdc440d09fa1f52ea95e&o=",
        "stars": 4,
        "review_score": 9.5,
        "review_score_word": "Exceptional",
        "review_count": 1272,
        "price": 867.89,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 11039130,
        "name": "Art Legacy Hotel Baixa-Chiado",
        "latitude": 38.711051792954,
        "longitude": -9.138808924537,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/735702231.jpg?k=78b5974474f85b763f7aeb445f66c71f4f10442d6ed78c1ef0315c205955ec6b&o=",
        "stars": 5,
        "review_score": 9.5,
        "review_score_word": "Exceptional",
        "review_count": 1136,
        "price": 1605.00,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 2628938,
        "name": "Villa Baixa - Lisbon Luxury Apartments",
        "latitude": 38.7124951804023,
        "longitude": -9.13769279818235,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/736934046.jpg?k=6515433d836ce51d62f57ac9b2da7c18c690bf8cdd2a0cafd319b99f2935ee33&o=",
        "stars": 4,
        "review_score": 9.5,
        "review_score_word": "Exceptional",
        "review_count": 910,
        "price": 1308.34,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "11:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 6343839,
        "name": "The Homeboat Company Parque das Nações-Lisboa",
        "latitude": 38.7547868740476,
        "longitude": -9.09406424669647,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/504381563.jpg?k=c1cde084771b26326445e7cbfd3d61ccbf12ae5220b59d96a462b58d0b69da7a&o=",
        "stars": 0,
        "review_score": 9.5,
        "review_score_word": "Exceptional",
        "review_count": 2863,
        "price": 1249.42,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 6733568,
        "name": "Blue Liberdade Hotel",
        "latitude": 38.715467,
        "longitude": -9.140805,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/336537962.jpg?k=6936029b29d81cfd66dfa138941b296222f3b136c9478679404297735b44069d&o=",
        "stars": 3,
        "review_score": 9.4,
        "review_score_word": "Wonderful",
        "review_count": 1915,
        "price": 994.48,
        "currency": "EUR",
        "checkin_from": "16:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 13731282,
        "name": "LIOZ Lisboa",
        "latitude": 38.7090128,
        "longitude": -9.1314054,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/721228000.jpg?k=e0e2a3b1713320dba66916fca925d1f2e6e9049743fbdfd23a93915d89821e75&o=",
        "stars": 4,
        "review_score": 9.5,
        "review_score_word": "Exceptional",
        "review_count": 255,
        "price": 2776.42,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 2843226,
        "name": "Hotel da Baixa",
        "latitude": 38.7125632,
        "longitude": -9.13754930000005,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/119467751.jpg?k=44c6af04059959ba51047298f308a81d42e0055dd82d0a90a5af8ea4bbe97bcb&o=",
        "stars": 4,
        "review_score": 9.4,
        "review_score_word": "Wonderful",
        "review_count": 1352,
        "price": 1311.71,
        "currency": "EUR",
        "checkin_from": "16:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 41251,
        "name": "Olissippo Lapa Palace – The Leading Hotels of the World",
        "latitude": 38.7068047689492,
        "longitude": -9.16383817791939,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/771929899.jpg?k=36dd7f04446021525caea5fbaab9e0603508ab5a7a9a0d488d613e00d8565048&o=",
        "stars": 5,
        "review_score": 9.4,
        "review_score_word": "Wonderful",
        "review_count": 359,
        "price": 4825.47,
        "currency": "EUR",
        "checkin_from": "14:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 14764658,
        "name": "MACAM Hotel",
        "latitude": 38.7004716009154,
        "longitude": -9.18334187798767,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/731790994.jpg?k=06f0d4cc165938cfa6e9da32959b786f468b7aeca1621ac8c3cae931935eabd1&o=",
        "stars": 5,
        "review_score": 9.6,
        "review_score_word": "Exceptional",
        "review_count": 146,
        "price": 1622.15,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 1838793,
        "name": "Chiado Square Apartments | Lisbon Best Apartments",
        "latitude": 38.7107086163126,
        "longitude": -9.14200628465574,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/632175066.jpg?k=0a522525b7c43a5788dc90ee59647b11886316f949c50a96576d3829f5f96c98&o=",
        "stars": 4,
        "review_score": 9.6,
        "review_score_word": "Exceptional",
        "review_count": 285,
        "price": 2036.32,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 7249141,
        "name": "Vincci Alfama",
        "latitude": 38.713349,
        "longitude": -9.127786,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/678086377.jpg?k=026d566cf0cade355d33ba0a2abc29ae8886c30c8c4b49aee6300b1b2f9e3549&o=",
        "stars": 4,
        "review_score": 9.3,
        "review_score_word": "Wonderful",
        "review_count": 988,
        "price": 850.00,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 3686645,
        "name": "Marques Best Apartments | Lisbon Best Apartments",
        "latitude": 38.727633,
        "longitude": -9.146756,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/506331577.jpg?k=86d205bbc7167b6b2890d97fa2e799f3806ba0cbb95176e6f822922d8b5bd03f&o=",
        "stars": 4,
        "review_score": 9.5,
        "review_score_word": "Exceptional",
        "review_count": 270,
        "price": 1178.80,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 15781550,
        "name": "Olympia Lis Boutique Hotel",
        "latitude": 38.7166656,
        "longitude": -9.1414034,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/820833824.jpg?k=4fe2debad1c9befa3d7ece764f0161314eb19010d7a7d96c481b9994779478e6&o=",
        "stars": 4,
        "review_score": 9.6,
        "review_score_word": "Exceptional",
        "review_count": 189,
        "price": 1219.06,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 8060119,
        "name": "Hotel Hotel Lisboa, a Member of Design Hotels",
        "latitude": 38.7171265361203,
        "longitude": -9.14400156888763,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/340369049.jpg?k=1f30205f402f6a008a63a7bafb8cc7a645032fea82f8300870661b1077ad5c69&o=",
        "stars": 4,
        "review_score": 9.4,
        "review_score_word": "Wonderful",
        "review_count": 1607,
        "price": 1000.21,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 2030901,
        "name": "The Lisboans Apartments",
        "latitude": 38.7106538919699,
        "longitude": -9.13476652023769,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/94866853.jpg?k=3df0d81fdbd8a2e6de25d00c7590434a359aeb567ba504f0eac1dc87b1b755a9&o=",
        "stars": 4,
        "review_score": 9.5,
        "review_score_word": "Exceptional",
        "review_count": 361,
        "price": 1425.72,
        "currency": "EUR",
        "checkin_from": "15:00",
        "checkout_until": "11:00",
        "country_code": "pt",
    },
    {
        "hotel_id": 1958504,
        "name": "Lisboa Pessoa Hotel",
        "latitude": 38.7125450592767,
        "longitude": -9.14151477682094,
        "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/569764275.jpg?k=48038a83c082191b5a590551b70dd071795a8af60cc68b45f133a4accbc8c257&o=",
        "stars": 4,
        "review_score": 9.4,
        "review_score_word": "Wonderful",
        "review_count": 3101,
        "price": 910.08,
        "currency": "EUR",
        "checkin_from": "16:00",
        "checkout_until": "12:00",
        "country_code": "pt",
    },
]


class FakeBookingClient(HotelDestinationProvider, HotelSearchProvider, HotelDetailsProvider):
    """Returns hardcoded results for local dev when no API key is set."""

    async def search_destinations(self, query: str) -> list[HotelDestination]:
        query_lower = query.lower()
        results: list[HotelDestination] = [
            HotelDestination(
                dest_id=item["dest_id"],
                city_name=item["city_name"],
                label=item["label"],
            )
            for item in _FAKE_DESTINATIONS
            if query_lower in item["city_name"].lower()
            or query_lower in item["label"].lower()
        ]
        # If nothing matches the filter, return all fake data so the endpoint is never empty
        if not results:
            results = [
                HotelDestination(
                    dest_id=item["dest_id"],
                    city_name=item["city_name"],
                    label=item["label"],
                )
                for item in _FAKE_DESTINATIONS
            ]
        return results

    async def search_hotels(
        self,
        dest_id: str,
        search_type: str,
        arrival_date: str,
        departure_date: str,
        adults: int,
        room_qty: int,
        page_number: int,
        currency_code: str,
        sort_by: str,
        price_min: int | None,
        price_max: int | None,
    ) -> list[HotelOffer]:
        # Compute number of nights from dates
        nights: int = 5  # default
        try:
            checkin_dt = DateType.fromisoformat(arrival_date)
            checkout_dt = DateType.fromisoformat(departure_date)
            diff = (checkout_dt - checkin_dt).days
            if diff > 0:
                nights = diff
        except ValueError:
            pass

        results: list[HotelOffer] = []
        for h in _FAKE_HOTELS:
            total = h["price"]
            per_night = round(total / nights, 2)
            # Approximate excluded (tax) as ~7% of total (based on real API data)
            excluded = round(total * 0.07, 2)
            results.append(
                HotelOffer(
                    hotel_id=h["hotel_id"],
                    name=h["name"],
                    latitude=h["latitude"],
                    longitude=h["longitude"],
                    photo_url=h["photo_url"],
                    stars=h["stars"],
                    review_score=h["review_score"],
                    review_score_word=h["review_score_word"],
                    review_count=h["review_count"],
                    price_total=total,
                    price_per_night=per_night,
                    price_excluded=excluded,
                    currency=h["currency"],
                    checkin_from=h["checkin_from"],
                    checkout_until=h["checkout_until"],
                    country_code=h["country_code"],
                )
            )

        # Apply basic price filtering on fake data
        if price_min is not None:
            results = [h for h in results if h.price_total >= price_min]
        if price_max is not None:
            results = [h for h in results if h.price_total <= price_max]

        return results

    async def get_hotel_details(
        self,
        hotel_id: int,
        arrival_date: str,
        departure_date: str,
        adults: int,
        room_qty: int,
        currency_code: str,
    ) -> HotelDetails | None:
        # Find matching fake hotel or return a generic one
        matching = [h for h in _FAKE_HOTELS if h["hotel_id"] == hotel_id]
        hotel = matching[0] if matching else _FAKE_HOTELS[0]

        # Compute nights for per-night price
        nights: int = 5
        try:
            checkin_dt = DateType.fromisoformat(arrival_date)
            checkout_dt = DateType.fromisoformat(departure_date)
            diff = (checkout_dt - checkin_dt).days
            if diff > 0:
                nights = diff
        except ValueError:
            pass

        total = hotel["price"]
        per_night = round(total / nights, 2)
        excluded = round(total * 0.07, 2)

        return HotelDetails(
            hotel_id=hotel["hotel_id"],
            name=hotel["name"],
            url=f"https://www.booking.com/hotel/pt/{hotel['hotel_id']}.html",
            description="Set in the heart of Lisbon, this property offers elegant rooms with modern amenities, a rooftop terrace with panoramic city views, and easy access to major attractions.",
            latitude=hotel["latitude"],
            longitude=hotel["longitude"],
            address="Rua do Ouro 123",
            city="Lisbon",
            district="Santa Maria Maior",
            country="Portugal",
            country_code=hotel["country_code"],
            zip_code="1100-060",
            accommodation_type="Hotels",
            stars=hotel["stars"],
            review_score=hotel["review_score"],
            review_score_word=hotel["review_score_word"],
            review_count=hotel["review_count"],
            currency=hotel["currency"],
            price_per_night=per_night,
            price_total=total,
            price_excluded=excluded,
            available_rooms=3,
            breakfast_included=True,
            checkin_from=hotel["checkin_from"],
            checkin_until="00:00",
            checkout_from="00:00",
            checkout_until=hotel["checkout_until"],
            distance_to_center_km=1.2,
            facilities=["Free WiFi", "Swimming pool", "Restaurant", "Spa", "Free parking", "Air conditioning"],
            photos=[
                hotel["photo_url"],
                "https://cf.bstatic.com/xdata/images/hotel/max1280x900/466945356.jpg",
                "https://cf.bstatic.com/xdata/images/hotel/max1280x900/508051702.jpg",
            ],
            rooms=[
                HotelRoom(
                    room_id="101",
                    description="Spacious room with city view, flat-screen TV, and rain shower.",
                    photos=[
                        hotel["photo_url"],
                    ],
                    highlights=[
                        HotelRoomHighlight(name="Free WiFi", icon="wifi"),
                        HotelRoomHighlight(name="Air conditioning", icon="snowflake"),
                        HotelRoomHighlight(name="City view", icon="city"),
                    ],
                    bed_configurations=["1 double bed"],
                    room_surface_m2=35.0,
                )
            ],
        )

