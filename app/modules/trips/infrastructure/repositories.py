from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.trips.domain.entities import (
    SavedFlight,
    SavedFlightLeg,
    Trip,
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
        doc = await self._col.find_one({"_id": oid, "user_id": user_id})
        return self._to_entity(doc) if doc else None

    async def list_by_user(self, user_id: str) -> list[Trip]:
        cursor = self._col.find({"user_id": user_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        return [self._to_entity(d) for d in docs]

    # ── Index ────────────────────────────────────────────────────────────────

    async def ensure_indexes(self) -> None:
        await self._col.create_index("user_id")

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

        return {
            "user_id": trip.user_id,
            "outbound_flight": flight_doc(trip.outbound_flight),
            "return_flight": flight_doc(trip.return_flight),
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

        return Trip(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            outbound_flight=parse_flight(doc["outbound_flight"]),
            return_flight=parse_flight(doc["return_flight"]),
            status=TripStatus(doc.get("status", "planning")),
            created_at=doc.get("created_at", datetime.utcnow()),
            updated_at=doc.get("updated_at", datetime.utcnow()),
        )

