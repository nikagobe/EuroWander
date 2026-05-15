from pydantic import BaseModel, ConfigDict

from app.modules.cities.domain.entities import City


class CityResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "wikidata_id": "Q90",
                "name": "Paris",
                "description": "capital and largest city of France",
                "country": "France",
                "freebase_id": "/m/05qtj",
                "lat": 48.8566,
                "lng": 2.3522,
            }
        }
    )

    wikidata_id: str
    name: str
    description: str
    country: str
    freebase_id: str
    lat: float | None = None
    lng: float | None = None

    @classmethod
    def from_entity(cls, city: City) -> "CityResponse":
        return cls(
            wikidata_id=city.wikidata_id,
            name=city.name,
            description=city.description,
            country=city.country,
            freebase_id=city.freebase_id,
            lat=city.lat,
            lng=city.lng,
        )
