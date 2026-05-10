from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str
    database_name: str = "eurowander"
    secret_key: str
    serpapi_key: str = ""
    rapidapi_key: str = ""
    google_places_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()

