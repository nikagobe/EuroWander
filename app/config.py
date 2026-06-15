from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Only load .env if it actually exists (it won't on Lambda)
_env_file = ".env" if Path(".env").exists() else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongodb_uri: str
    database_name: str = "eurowander"
    secret_key: str
    serpapi_key: str = ""
    rapidapi_key: str = ""
    google_places_key: str = ""
    # AWS S3 (object storage for documents)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket_name: str = ""
    aws_s3_region: str = "eu-central-1"
    s3_url_expiration_seconds: int = 3600  # presigned URL lifetime (1 hour)
    document_max_size_bytes: int = 10_485_760  # 10 MB
    # Comma-separated list of allowed origins, or "*" to allow all.
    cors_origins: list[str] = ["*"]



settings = Settings()

