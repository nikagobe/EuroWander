from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.trips.domain.entities import (
    SavedBusJourney,
    SavedBusSegment,
    SavedFlight,
    SavedFlightLeg,
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

    # ── Index ────────────────────────────────────────────────────────────────

    async def ensure_indexes(self) -> None:
        await self._col.create_index("user_id")
        await self._col.create_index("members.user_id")

    # ── Mapping ──────────────────────────────────────────────────────────────

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
            }

        def bus_doc(b: SavedBusJourney) -> dict:
            return {
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
            }

        return {
            "user_id": trip.user_id,
            "name": trip.name,
            "members": [
                {"user_id": m.user_id, "role": m.role.value, "joined_at": m.joined_at}
                for m in trip.members
            ],
            "outbound_flight": flight_doc(trip.outbound_flight),
            "return_flight": flight_doc(trip.return_flight),
            "bus_journey": bus_doc(trip.bus_journey) if trip.bus_journey is not None else None,
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
            )

        def parse_bus(d: dict) -> SavedBusJourney:
            return SavedBusJourney(
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
            )

        bus_data = doc.get("bus_journey")

        members = [
            TripMember(
                user_id=m["user_id"],
                role=TripRole(m.get("role", "member")),
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
            status=TripStatus(doc.get("status", "planning")),
            created_at=doc.get("created_at", datetime.utcnow()),
            updated_at=doc.get("updated_at", datetime.utcnow()),
        )

