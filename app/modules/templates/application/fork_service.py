"""
Fork Service — orchestrates creating a Trip from a Template.

This service coordinates between the templates, playlists, and trips modules
to produce a fully populated Trip from a template fork.
"""

from datetime import datetime, timedelta

from app.modules.playlists.domain.entities import PlaylistItemType
from app.modules.playlists.domain.interfaces import PlaylistRepository
from app.modules.templates.domain.interfaces import TemplateRepository
from app.modules.trips.domain.entities import (
    SavedAttraction,
    SavedBusJourney,
    SavedFlight,
    SavedHotel,
    SavedRestaurant,
    Trip,
    TripMember,
    TripRole,
)
from app.modules.trips.domain.interfaces import TripRepository


class ForkService:
    """Orchestrates creating a full Trip from a template fork."""

    def __init__(
        self,
        template_repo: TemplateRepository,
        trip_repo: TripRepository,
        playlist_repo: PlaylistRepository,
    ) -> None:
        self._template_repo = template_repo
        self._trip_repo = trip_repo
        self._playlist_repo = playlist_repo

    async def create_trip_from_template(
        self,
        template_id: str,
        user_id: str,
        user_first_name: str,
        user_last_name: str,
        name: str,
        start_date: str,
        outbound_flight: SavedFlight,
        return_flight: SavedFlight | None,
        hotels: list[SavedHotel],
        buses: list[SavedBusJourney],
    ) -> Trip | None:
        """
        Create a Trip from a template:
        1. Validate template exists and is published
        2. Copy attractions & restaurants from template playlists
        3. Assign concrete dates based on start_date + leg day offsets
        4. Save hotels, flights, buses
        5. Increment fork count
        6. Return the created Trip
        """
        template = await self._template_repo.get_by_id(template_id)
        if template is None or not template.is_published():
            return None

        if not template.legs:
            return None

        # Calculate date offsets for each leg
        base_date = datetime.strptime(start_date, "%Y-%m-%d")
        leg_date_map: dict[int, datetime] = {}  # order -> start date of that leg
        current_date = base_date
        for leg in sorted(template.legs, key=lambda l: l.order):
            leg_date_map[leg.order] = current_date
            current_date += timedelta(days=leg.days)

        # Collect attractions and restaurants from playlists
        attractions: list[SavedAttraction] = []
        restaurants: list[SavedRestaurant] = []

        for leg in template.legs:
            leg_start = leg_date_map[leg.order]

            # Fetch playlist items if playlist_id exists
            if leg.playlist_id:
                playlist = await self._playlist_repo.get_by_id(leg.playlist_id)
                if playlist:
                    for item in playlist.items:
                        # Calculate concrete date from day_number
                        item_date = leg_start + timedelta(days=item.day_number - 1)
                        date_str = item_date.strftime("%Y-%m-%d")

                        if item.item_type == PlaylistItemType.ATTRACTION:
                            attractions.append(SavedAttraction(
                                location_id=item.location_id,
                                name=item.name,
                                category=item.category,
                                photo_url=item.photo_url,
                                latitude=item.latitude,
                                longitude=item.longitude,
                                address=item.address,
                                rating=item.rating,
                                num_reviews=item.num_reviews,
                                ticket_price=item.price_indicator,
                                day_date=date_str,
                                time_slot=item.time_slot.value,
                            ))
                        elif item.item_type == PlaylistItemType.RESTAURANT:
                            restaurants.append(SavedRestaurant(
                                location_id=item.location_id,
                                name=item.name,
                                cuisine=item.category,
                                photo_url=item.photo_url,
                                latitude=item.latitude,
                                longitude=item.longitude,
                                address=item.address,
                                rating=item.rating,
                                num_reviews=item.num_reviews,
                                price_level=item.price_indicator,
                                day_date=date_str,
                                time_slot=item.time_slot.value,
                            ))

        # Determine destination photo from template cover or first leg city
        destination_image = template.cover_photo_url or ""

        # Build the first bus as the primary bus_journey (legacy single-bus field)
        primary_bus: SavedBusJourney | None = buses[0] if buses else None

        # Create master member
        master = TripMember(
            user_id=user_id,
            role=TripRole.MASTER,
            first_name=user_first_name,
            last_name=user_last_name,
        )

        # Build a dummy return flight if none provided (empty placeholder)
        if return_flight is None:
            return_flight_val = SavedFlight(
                flight_id="",
                price=0.0,
                currency="EUR",
                total_duration_minutes=0,
                stops=0,
                airline_logo="",
                booking_token="",
                legs=[],
            )
        else:
            return_flight_val = return_flight

        trip = Trip(
            user_id=user_id,
            name=name,
            outbound_flight=outbound_flight,
            return_flight=return_flight_val,
            bus_journey=primary_bus,
            hotels=hotels,
            attractions=attractions,
            restaurants=restaurants,
            members=[master],
            forked_from_template_id=template_id,
            destination_image_filename="",
            destination_image_url=destination_image,
        )

        created_trip = await self._trip_repo.create(trip)

        # Increment fork count on template
        await self._template_repo.increment_fork_count(template_id)

        return created_trip



