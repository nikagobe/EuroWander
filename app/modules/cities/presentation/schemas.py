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
            }
        }
    )

    wikidata_id: str
    name: str
    description: str
    country: str
    freebase_id: str   # pass this as origin_id / destination_id in flight search

    @classmethod
    def from_entity(cls, city: City) -> "CityResponse":
        return cls(
            wikidata_id=city.wikidata_id,
            name=city.name,
            description=city.description,
            country=city.country,
            freebase_id=city.freebase_id,
        )

