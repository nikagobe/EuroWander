"""
Profile application service — orchestrates domain logic and repositories.
No FastAPI or Pydantic imports here.
"""

from collections import Counter
from datetime import datetime

from app.modules.airports.domain.interfaces import AirportRepository
from app.modules.profiles.domain.badge_rules import compute_badges
from app.modules.profiles.domain.distance import haversine_km
from app.modules.profiles.domain.entities import (
    Badge,
    FrequentCollaborator,
    TravelStats,
    UserProfile,
)
from app.modules.profiles.domain.interfaces import ProfileRepository
from app.modules.trips.domain.entities import Trip, TripStatus
from app.modules.trips.domain.interfaces import TripRepository


class ProfileService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        trip_repo: TripRepository,
        airport_repo: AirportRepository,
    ) -> None:
        self._profile_repo = profile_repo
        self._trip_repo = trip_repo
        self._airport_repo = airport_repo

    # ── Profile CRUD ──────────────────────────────────────────────────────────

    async def get_profile(self, user_id: str) -> UserProfile:
        """Return the user's profile, creating a blank one if it doesn't exist."""
        profile = await self._profile_repo.get_by_user_id(user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
            profile = await self._profile_repo.upsert(profile)
        return profile

    async def update_profile(
        self,
        user_id: str,
        *,
        bio: str | None = None,
        home_city: str | None = None,
        base_airport: str | None = None,
        profile_photo_url: str | None = None,
        cover_photo_url: str | None = None,
        preferred_languages: list[str] | None = None,
        travel_style_tags: list[str] | None = None,
    ) -> UserProfile:
        """Partially update personalization fields."""
        profile = await self.get_profile(user_id)
        if bio is not None:
            profile.bio = bio
        if home_city is not None:
            profile.home_city = home_city
        if base_airport is not None:
            profile.base_airport = base_airport
        if profile_photo_url is not None:
            profile.profile_photo_url = profile_photo_url
        if cover_photo_url is not None:
            profile.cover_photo_url = cover_photo_url
        if preferred_languages is not None:
            profile.preferred_languages = preferred_languages
        if travel_style_tags is not None:
            profile.travel_style_tags = travel_style_tags
        profile.updated_at = datetime.utcnow()
        return await self._profile_repo.upsert(profile)

    # ── Travel Statistics ─────────────────────────────────────────────────────

    async def get_stats(self, user_id: str) -> TravelStats:
        """Compute travel statistics from completed trips."""
        completed = await self._trip_repo.list_by_user_status(user_id, TripStatus.COMPLETED)

        city_counter: Counter[str] = Counter()
        total_distance = 0.0

        for trip in completed:
            # Collect destination cities from flight arrival airports
            for flight in (trip.outbound_flight, trip.return_flight):
                for leg in flight.legs:
                    arr_name = leg.arrival_airport_name
                    if arr_name:
                        city_counter[arr_name] += 1

            # Compute distance from flight leg airports
            for flight in (trip.outbound_flight, trip.return_flight):
                for leg in flight.legs:
                    dep = await self._airport_repo.get_by_iata(leg.departure_airport)
                    arr = await self._airport_repo.get_by_iata(leg.arrival_airport)
                    if dep and arr and dep.lat and dep.lng and arr.lat and arr.lng:
                        total_distance += haversine_km(dep.lat, dep.lng, arr.lat, arr.lng)

        cities = list(city_counter.keys())
        favorite = city_counter.most_common(1)[0][0] if city_counter else ""

        return TravelStats(
            trips_completed=len(completed),
            cities_visited=cities,
            total_distance_km=round(total_distance, 1),
            favorite_destination=favorite,
        )

    # ── Badges ────────────────────────────────────────────────────────────────

    async def get_badges(self, user_id: str) -> list[Badge]:
        """Compute earned badges from trip data."""
        all_trips = await self._trip_repo.list_by_user(user_id)
        completed = [t for t in all_trips if t.status == TripStatus.COMPLETED]

        # Count unique countries via airport country codes
        country_codes: set[str] = set()
        flight_count = 0
        bus_count = 0

        for trip in completed:
            for flight in (trip.outbound_flight, trip.return_flight):
                flight_count += 1
                for leg in flight.legs:
                    apt = await self._airport_repo.get_by_iata(leg.arrival_airport)
                    if apt:
                        country_codes.add(apt.country_code)

            if trip.bus_journey is not None:
                bus_count += 1

        trips_created = await self._trip_repo.count_created_by_user(user_id)
        shared_trips = sum(1 for t in all_trips if len(t.members) > 0)

        return compute_badges(
            trips_completed=len(completed),
            trips_created=trips_created,
            countries_visited_count=len(country_codes),
            flight_count=flight_count,
            bus_count=bus_count,
            shared_trip_count=shared_trips,
        )

    # ── Frequent Collaborators ────────────────────────────────────────────────

    async def get_collaborators(
        self, user_id: str, limit: int = 5
    ) -> list[FrequentCollaborator]:
        """Top N users this person has shared the most trips with."""
        all_trips = await self._trip_repo.list_by_user(user_id)

        co_traveller_counter: Counter[str] = Counter()
        member_info: dict[str, tuple[str, str]] = {}  # user_id -> (first, last)

        for trip in all_trips:
            # Collect all participant IDs (owner + members) excluding self
            participant_ids: set[str] = {trip.user_id}
            for m in trip.members:
                participant_ids.add(m.user_id)
                if m.user_id != user_id:
                    member_info[m.user_id] = (m.first_name, m.last_name)

            # If trip owner is someone else, record them too
            if trip.user_id != user_id:
                # We don't have owner names in trip doc directly — stored as member_info if they appear
                pass

            participant_ids.discard(user_id)
            for pid in participant_ids:
                co_traveller_counter[pid] += 1

        # Get profile photos for top collaborators
        top = co_traveller_counter.most_common(limit)
        collaborators: list[FrequentCollaborator] = []
        for collab_id, count in top:
            first, last = member_info.get(collab_id, ("", ""))
            # Look up their profile photo
            collab_profile = await self._profile_repo.get_by_user_id(collab_id)
            photo = collab_profile.profile_photo_url if collab_profile else ""
            collaborators.append(
                FrequentCollaborator(
                    user_id=collab_id,
                    first_name=first,
                    last_name=last,
                    profile_photo_url=photo,
                    shared_trip_count=count,
                )
            )

        return collaborators

    # ── Activity Feed ─────────────────────────────────────────────────────────

    async def get_activity_feed(
        self, user_id: str, limit: int = 10
    ) -> dict[str, list[Trip]]:
        """Return recent completed trips and upcoming (planning/booked) trips."""
        completed = await self._trip_repo.list_by_user_status(user_id, TripStatus.COMPLETED)
        planning = await self._trip_repo.list_by_user_status(user_id, TripStatus.PLANNING)
        booked = await self._trip_repo.list_by_user_status(user_id, TripStatus.BOOKED)

        upcoming = sorted(planning + booked, key=lambda t: t.created_at, reverse=True)

        return {
            "recent_completed": completed[:limit],
            "upcoming": upcoming[:limit],
        }

