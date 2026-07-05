from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.trips.domain.entities import (
    SavedAttraction,
    SavedBusJourney,
    SavedBusSegment,
    SavedFlight,
    SavedFlightLeg,
    SavedHotel,
    SavedRestaurant,
    Trip,
    TripMember,
    TripRole,
    TripStatus,
)
from app.modules.trips.domain.interfaces import TripRepository


class MongoTripRepository(TripRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    # ── Write ────────────────────────────────────────────────────────────────

    async def create(self, trip: Trip) -> Trip:
        doc = self._to_doc(trip)
        result = await self._col.insert_one(doc)
        trip.id = str(result.inserted_id)
        return trip

    async def delete(self, trip_id: str, user_id: str) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.delete_one({"_id": oid, "user_id": user_id})
        return result.deleted_count == 1

    # ── Read ─────────────────────────────────────────────────────────────────

    async def get_by_id(self, trip_id: str, user_id: str) -> Trip | None:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return None
        # Accessible if user is owner OR listed in members
        doc = await self._col.find_one({
            "_id": oid,
            "$or": [{"user_id": user_id}, {"members.user_id": user_id}],
        })
        return self._to_entity(doc) if doc else None

    async def get_by_id_any_user(self, trip_id: str) -> Trip | None:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return None
        doc = await self._col.find_one({"_id": oid})
        return self._to_entity(doc) if doc else None

    async def list_by_user(self, user_id: str) -> list[Trip]:
        # Include trips where user is owner OR a member
        cursor = self._col.find({
            "$or": [{"user_id": user_id}, {"members.user_id": user_id}]
        }).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        return [self._to_entity(d) for d in docs]

    async def add_member(self, trip_id: str, member: TripMember) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid},
            {"$push": {"members": {
                "user_id": member.user_id,
                "role": member.role.value,
                "first_name": member.first_name,
                "last_name": member.last_name,
                "joined_at": member.joined_at,
            }}},
        )
        return result.modified_count == 1

    async def remove_member(self, trip_id: str, member_user_id: str) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid},
            {"$pull": {"members": {"user_id": member_user_id}}},
        )
        return result.modified_count == 1

    async def update_flight_payment(
        self,
        trip_id: str,
        flight_type: str,
        is_paid: bool,
        actual_paid_amount: float | None,
        paid_currency: str | None,
        paid_by: str | None,
        eligible_member_ids: list[str],
    ) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        field_prefix = "outbound_flight" if flight_type == "outbound" else "return_flight"
        result = await self._col.update_one(
            {"_id": oid},
            {"$set": {
                f"{field_prefix}.is_paid": is_paid,
                f"{field_prefix}.actual_paid_amount": actual_paid_amount,
                f"{field_prefix}.paid_currency": paid_currency,
                f"{field_prefix}.paid_by": paid_by,
                f"{field_prefix}.eligible_member_ids": eligible_member_ids,
                "updated_at": datetime.utcnow(),
            }},
        )
        return result.modified_count == 1

    async def update_bus_payment(
        self,
        trip_id: str,
        is_paid: bool,
        actual_paid_amount: float | None,
        paid_currency: str | None,
        paid_by: str | None,
        eligible_member_ids: list[str],
    ) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid, "bus_journey": {"$ne": None}},
            {"$set": {
                "bus_journey.is_paid": is_paid,
                "bus_journey.actual_paid_amount": actual_paid_amount,
                "bus_journey.paid_currency": paid_currency,
                "bus_journey.paid_by": paid_by,
                "bus_journey.eligible_member_ids": eligible_member_ids,
                "updated_at": datetime.utcnow(),
            }},
        )
        return result.modified_count == 1

    async def add_hotel(self, trip_id: str, hotel: SavedHotel) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid},
            {
                "$push": {"hotels": self._hotel_doc(hotel)},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return result.modified_count == 1

    async def remove_hotel(self, trip_id: str, hotel_id: int) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid, "hotels.hotel_id": hotel_id},
            {
                "$pull": {"hotels": {"hotel_id": hotel_id}},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return result.modified_count == 1

    async def update_hotel_payment(
        self,
        trip_id: str,
        hotel_id: int,
        is_paid: bool,
        actual_paid_amount: float | None,
        paid_currency: str | None,
        paid_by: str | None,
        eligible_member_ids: list[str],
    ) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid, "hotels.hotel_id": hotel_id},
            {"$set": {
                "hotels.$.is_paid": is_paid,
                "hotels.$.actual_paid_amount": actual_paid_amount,
                "hotels.$.paid_currency": paid_currency,
                "hotels.$.paid_by": paid_by,
                "hotels.$.eligible_member_ids": eligible_member_ids,
                "updated_at": datetime.utcnow(),
            }},
        )
        return result.modified_count == 1

    # ── Attraction management ─────────────────────────────────────────────────

    async def add_attraction(self, trip_id: str, attraction: SavedAttraction) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid},
            {
                "$push": {"attractions": self._attraction_doc(attraction)},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return result.modified_count == 1

    async def remove_attraction(self, trip_id: str, location_id: str) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid, "attractions.location_id": location_id},
            {
                "$pull": {"attractions": {"location_id": location_id}},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return result.modified_count == 1

    async def update_attraction_payment(
        self,
        trip_id: str,
        location_id: str,
        is_paid: bool,
        actual_paid_amount: float | None,
        paid_currency: str | None,
        paid_by: str | None,
        eligible_member_ids: list[str],
    ) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid, "attractions.location_id": location_id},
            {"$set": {
                "attractions.$.is_paid": is_paid,
                "attractions.$.actual_paid_amount": actual_paid_amount,
                "attractions.$.paid_currency": paid_currency,
                "attractions.$.paid_by": paid_by,
                "attractions.$.eligible_member_ids": eligible_member_ids,
                "updated_at": datetime.utcnow(),
            }},
        )
        return result.modified_count == 1

    # ── Restaurant management ─────────────────────────────────────────────────

    async def add_restaurant(self, trip_id: str, restaurant: SavedRestaurant) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid},
            {
                "$push": {"restaurants": self._restaurant_doc(restaurant)},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return result.modified_count == 1

    async def remove_restaurant(self, trip_id: str, location_id: str) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid, "restaurants.location_id": location_id},
            {
                "$pull": {"restaurants": {"location_id": location_id}},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return result.modified_count == 1

    async def update_restaurant_payment(
        self,
        trip_id: str,
        location_id: str,
        is_paid: bool,
        actual_paid_amount: float | None,
        paid_currency: str | None,
        paid_by: str | None,
        eligible_member_ids: list[str],
    ) -> bool:
        try:
            oid = ObjectId(trip_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid, "restaurants.location_id": location_id},
            {"$set": {
                "restaurants.$.is_paid": is_paid,
                "restaurants.$.actual_paid_amount": actual_paid_amount,
                "restaurants.$.paid_currency": paid_currency,
                "restaurants.$.paid_by": paid_by,
                "restaurants.$.eligible_member_ids": eligible_member_ids,
                "updated_at": datetime.utcnow(),
            }},
        )
        return result.modified_count == 1

    # ── Index ─────────────────────────────────────────────────────────────────

    async def ensure_indexes(self) -> None:
        await self._col.create_index("user_id")
        await self._col.create_index("members.user_id")

    # ── Mapping ──────────────────────────────────────────────────────────────

    @staticmethod
    def _hotel_doc(h: SavedHotel) -> dict:
        return {
            "hotel_id": h.hotel_id,
            "name": h.name,
            "city": h.city,
            "address": h.address,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "photo_url": h.photo_url,
            "stars": h.stars,
            "review_score": h.review_score,
            "review_score_word": h.review_score_word,
            "checkin_date": h.checkin_date,
            "checkout_date": h.checkout_date,
            "price_per_night": h.price_per_night,
            "price_total": h.price_total,
            "currency": h.currency,
            "booking_url": h.booking_url,
            "is_paid": h.is_paid,
            "actual_paid_amount": h.actual_paid_amount,
            "paid_currency": h.paid_currency,
            "paid_by": h.paid_by,
            "eligible_member_ids": h.eligible_member_ids,
        }

    @staticmethod
    def _attraction_doc(a: SavedAttraction) -> dict:
        return {
            "location_id": a.location_id,
            "name": a.name,
            "category": a.category,
            "photo_url": a.photo_url,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "address": a.address,
            "rating": a.rating,
            "num_reviews": a.num_reviews,
            "ticket_price": a.ticket_price,
            "day_date": a.day_date,
            "time_slot": a.time_slot,
            "is_paid": a.is_paid,
            "actual_paid_amount": a.actual_paid_amount,
            "paid_currency": a.paid_currency,
            "paid_by": a.paid_by,
            "eligible_member_ids": a.eligible_member_ids,
        }

    @staticmethod
    def _restaurant_doc(r: SavedRestaurant) -> dict:
        return {
            "location_id": r.location_id,
            "name": r.name,
            "cuisine": r.cuisine,
            "photo_url": r.photo_url,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "address": r.address,
            "rating": r.rating,
            "num_reviews": r.num_reviews,
            "price_level": r.price_level,
            "day_date": r.day_date,
            "time_slot": r.time_slot,
            "is_paid": r.is_paid,
            "actual_paid_amount": r.actual_paid_amount,
            "paid_currency": r.paid_currency,
            "paid_by": r.paid_by,
            "eligible_member_ids": r.eligible_member_ids,
        }

    @staticmethod
    def _to_doc(trip: Trip) -> dict:
        def leg_doc(leg: SavedFlightLeg) -> dict:
            return {
                "flight_number": leg.flight_number,
                "airline": leg.airline,
                "airline_logo": leg.airline_logo,
                "airplane": leg.airplane,
                "departure_airport": leg.departure_airport,
                "departure_airport_name": leg.departure_airport_name,
                "arrival_airport": leg.arrival_airport,
                "arrival_airport_name": leg.arrival_airport_name,
                "departure_time": leg.departure_time,
                "arrival_time": leg.arrival_time,
                "duration_minutes": leg.duration_minutes,
                "travel_class": leg.travel_class,
                "legroom": leg.legroom,
                "is_overnight": leg.is_overnight,
            }

        def flight_doc(f: SavedFlight) -> dict:
            return {
                "flight_id": f.flight_id,
                "price": f.price,
                "currency": f.currency,
                "total_duration_minutes": f.total_duration_minutes,
                "stops": f.stops,
                "airline_logo": f.airline_logo,
                "booking_token": f.booking_token,
                "legs": [leg_doc(l) for l in f.legs],
                "is_paid": f.is_paid,
                "actual_paid_amount": f.actual_paid_amount,
                "paid_currency": f.paid_currency,
                "paid_by": f.paid_by,
                "eligible_member_ids": f.eligible_member_ids,
            }

        def bus_doc(b: SavedBusJourney) -> dict:
            return {
                "journey_id": b.journey_id,
                "dep_name": b.dep_name,
                "arr_name": b.arr_name,
                "dep_time": b.dep_time,
                "arr_time": b.arr_time,
                "duration": b.duration,
                "duration_minutes": b.duration_minutes,
                "changeovers": b.changeovers,
                "price": b.price,
                "currency": b.currency,
                "deeplink": b.deeplink,
                "additional_info": b.additional_info,
                "segments": [
                    {
                        "dep_name": s.dep_name,
                        "arr_name": s.arr_name,
                        "dep_time": s.dep_time,
                        "arr_time": s.arr_time,
                        "product_type": s.product_type,
                        "product": s.product,
                    }
                    for s in b.segments
                ],
                "is_paid": b.is_paid,
                "actual_paid_amount": b.actual_paid_amount,
                "paid_currency": b.paid_currency,
                "paid_by": b.paid_by,
                "eligible_member_ids": b.eligible_member_ids,
            }

        return {
            "user_id": trip.user_id,
            "name": trip.name,
            "members": [
                {
                    "user_id": m.user_id,
                    "role": m.role.value,
                    "first_name": m.first_name,
                    "last_name": m.last_name,
                    "joined_at": m.joined_at,
                }
                for m in trip.members
            ],
            "outbound_flight": flight_doc(trip.outbound_flight),
            "return_flight": flight_doc(trip.return_flight),
            "bus_journey": bus_doc(trip.bus_journey) if trip.bus_journey is not None else None,
            "hotels": [MongoTripRepository._hotel_doc(h) for h in trip.hotels],
            "attractions": [MongoTripRepository._attraction_doc(a) for a in trip.attractions],
            "restaurants": [MongoTripRepository._restaurant_doc(r) for r in trip.restaurants],
            "status": trip.status.value,
            "created_at": trip.created_at,
            "updated_at": trip.updated_at,
        }

    @staticmethod
    def _to_entity(doc: dict) -> Trip:
        def parse_leg(d: dict) -> SavedFlightLeg:
            return SavedFlightLeg(
                flight_number=d["flight_number"],
                airline=d["airline"],
                airline_logo=d.get("airline_logo", ""),
                airplane=d.get("airplane", ""),
                departure_airport=d["departure_airport"],
                departure_airport_name=d.get("departure_airport_name", ""),
                arrival_airport=d["arrival_airport"],
                arrival_airport_name=d.get("arrival_airport_name", ""),
                departure_time=d["departure_time"],
                arrival_time=d["arrival_time"],
                duration_minutes=d["duration_minutes"],
                travel_class=d.get("travel_class", "Economy"),
                legroom=d.get("legroom", ""),
                is_overnight=d.get("is_overnight", False),
            )

        def parse_flight(d: dict) -> SavedFlight:
            return SavedFlight(
                flight_id=d["flight_id"],
                price=d["price"],
                currency=d["currency"],
                total_duration_minutes=d["total_duration_minutes"],
                stops=d["stops"],
                airline_logo=d.get("airline_logo", ""),
                booking_token=d.get("booking_token", ""),
                legs=[parse_leg(l) for l in d.get("legs", [])],
                is_paid=d.get("is_paid", False),
                actual_paid_amount=d.get("actual_paid_amount"),
                paid_currency=d.get("paid_currency"),
                paid_by=d.get("paid_by"),
                eligible_member_ids=d.get("eligible_member_ids", []),
            )

        def parse_bus(d: dict) -> SavedBusJourney:
            return SavedBusJourney(
                journey_id=d.get("journey_id", ""),
                dep_name=d.get("dep_name", ""),
                arr_name=d.get("arr_name", ""),
                dep_time=d.get("dep_time", ""),
                arr_time=d.get("arr_time", ""),
                duration=d.get("duration", ""),
                duration_minutes=d.get("duration_minutes", 0),
                changeovers=d.get("changeovers", 0),
                price=d.get("price", 0.0),
                currency=d.get("currency", "EUR"),
                deeplink=d.get("deeplink", ""),
                additional_info=d.get("additional_info", ""),
                segments=[
                    SavedBusSegment(
                        dep_name=s.get("dep_name", ""),
                        arr_name=s.get("arr_name", ""),
                        dep_time=s.get("dep_time", ""),
                        arr_time=s.get("arr_time", ""),
                        product_type=s.get("product_type", "bus"),
                        product=s.get("product", "flixbus"),
                    )
                    for s in d.get("segments", [])
                ],
                is_paid=d.get("is_paid", False),
                actual_paid_amount=d.get("actual_paid_amount"),
                paid_currency=d.get("paid_currency"),
                paid_by=d.get("paid_by"),
                eligible_member_ids=d.get("eligible_member_ids", []),
            )

        bus_data = doc.get("bus_journey")

        def parse_hotel(d: dict) -> SavedHotel:
            return SavedHotel(
                hotel_id=d.get("hotel_id", 0),
                name=d.get("name", ""),
                city=d.get("city", ""),
                address=d.get("address", ""),
                latitude=d.get("latitude", 0.0),
                longitude=d.get("longitude", 0.0),
                photo_url=d.get("photo_url", ""),
                stars=d.get("stars", 0),
                review_score=d.get("review_score", 0.0),
                review_score_word=d.get("review_score_word", ""),
                checkin_date=d.get("checkin_date", ""),
                checkout_date=d.get("checkout_date", ""),
                price_per_night=d.get("price_per_night", 0.0),
                price_total=d.get("price_total", 0.0),
                currency=d.get("currency", "EUR"),
                booking_url=d.get("booking_url", ""),
                is_paid=d.get("is_paid", False),
                actual_paid_amount=d.get("actual_paid_amount"),
                paid_currency=d.get("paid_currency"),
                paid_by=d.get("paid_by"),
                eligible_member_ids=d.get("eligible_member_ids", []),
            )

        # Backward compat: old docs may have "hotel" (single dict), new ones have "hotels" (list)
        hotels_raw: list[dict] = doc.get("hotels", [])
        old_hotel = doc.get("hotel")
        if not hotels_raw and old_hotel:
            hotels_raw = [old_hotel]
        hotels: list[SavedHotel] = [parse_hotel(h) for h in hotels_raw]

        def parse_attraction(d: dict) -> SavedAttraction:
            return SavedAttraction(
                location_id=d.get("location_id", ""),
                name=d.get("name", ""),
                category=d.get("category", ""),
                photo_url=d.get("photo_url", ""),
                latitude=d.get("latitude", 0.0),
                longitude=d.get("longitude", 0.0),
                address=d.get("address", ""),
                rating=d.get("rating", 0.0),
                num_reviews=d.get("num_reviews", 0),
                ticket_price=d.get("ticket_price", ""),
                day_date=d.get("day_date", ""),
                time_slot=d.get("time_slot", "morning"),
                is_paid=d.get("is_paid", False),
                actual_paid_amount=d.get("actual_paid_amount"),
                paid_currency=d.get("paid_currency"),
                paid_by=d.get("paid_by"),
                eligible_member_ids=d.get("eligible_member_ids", []),
            )

        attractions: list[SavedAttraction] = [
            parse_attraction(a) for a in doc.get("attractions", [])
        ]

        def parse_restaurant(d: dict) -> SavedRestaurant:
            return SavedRestaurant(
                location_id=d.get("location_id", ""),
                name=d.get("name", ""),
                cuisine=d.get("cuisine", ""),
                photo_url=d.get("photo_url", ""),
                latitude=d.get("latitude", 0.0),
                longitude=d.get("longitude", 0.0),
                address=d.get("address", ""),
                rating=d.get("rating", 0.0),
                num_reviews=d.get("num_reviews", 0),
                price_level=d.get("price_level", ""),
                day_date=d.get("day_date", ""),
                time_slot=d.get("time_slot", "evening"),
                is_paid=d.get("is_paid", False),
                actual_paid_amount=d.get("actual_paid_amount"),
                paid_currency=d.get("paid_currency"),
                paid_by=d.get("paid_by"),
                eligible_member_ids=d.get("eligible_member_ids", []),
            )

        restaurants: list[SavedRestaurant] = [
            parse_restaurant(r) for r in doc.get("restaurants", [])
        ]

        members = [
            TripMember(
                user_id=m["user_id"],
                role=TripRole(m.get("role", "member")),
                first_name=m.get("first_name", ""),
                last_name=m.get("last_name", ""),
                joined_at=m.get("joined_at", datetime.utcnow()),
            )
            for m in doc.get("members", [])
        ]

        return Trip(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            name=doc.get("name", ""),
            members=members,
            outbound_flight=parse_flight(doc["outbound_flight"]),
            return_flight=parse_flight(doc["return_flight"]),
            bus_journey=parse_bus(bus_data) if bus_data is not None else None,
            hotels=hotels,
            attractions=attractions,
            restaurants=restaurants,
            status=TripStatus(doc.get("status", "planning")),
            created_at=doc.get("created_at", datetime.utcnow()),
            updated_at=doc.get("updated_at", datetime.utcnow()),
        )

