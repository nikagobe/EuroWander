from pydantic_settings import BaseSettings


class Settings(BaseSettings):
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
    # Example in .env:  CORS_ORIGINS=http://localhost:3000,http://localhost:8080
    cors_origins: list[str] = ["*"]

    model_config = {"env_file": ".env"}


settings = Settings()

