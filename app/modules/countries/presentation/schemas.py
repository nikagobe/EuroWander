from pydantic import BaseModel, ConfigDict


class MajorCityResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Paris",
                "wikidata_id": "Q90",
                "freebase_id": "/m/05qtj",
                "description": "capital and largest city of France",
            }
        }
    )
    name: str
    wikidata_id: str
    freebase_id: str
    description: str


class CountryResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Spain",
                "neighbors": ["France", "Portugal", "Andorra"],
                "major_cities": [],
            }
        }
    )
    name: str
    neighbors: list[str]
    major_cities: list[MajorCityResponse]

