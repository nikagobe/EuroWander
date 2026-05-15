from pydantic import BaseModel, ConfigDict

from app.modules.airports.domain.entities import Airport


class AirportResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "wikidata_id": "Q161972",
                "name": "Paris Charles de Gaulle Airport",
                "iata_code": "CDG",
                "country_code": "FR",
                "lat": 49.0097,
                "lng": 2.5478,
            }
        }
    )

    wikidata_id: str
    name: str
    iata_code: str
    country_code: str
    lat: float | None = None
    lng: float | None = None

    @classmethod
    def from_entity(cls, a: Airport) -> "AirportResponse":
        return cls(
            wikidata_id=a.wikidata_id,
            name=a.name,
            iata_code=a.iata_code,
            country_code=a.country_code,
            lat=a.lat,
            lng=a.lng,
        )

