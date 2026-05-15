from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str
    database_name: str = "eurowander"
    secret_key: str
    serpapi_key: str = ""
    rapidapi_key: str = ""
    google_places_key: str = ""
    # Comma-separated list of allowed origins, or "*" to allow all.
    # Example in .env:  CORS_ORIGINS=http://localhost:3000,http://localhost:8080
    cors_origins: list[str] = ["*"]

    model_config = {"env_file": ".env"}


settings = Settings()

