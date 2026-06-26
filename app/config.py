from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Reads configuration from environment variables or a local .env file.
    Adding a new secret is as simple as adding a new typed field here —
    Pydantic Settings handles reading and validation automatically.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str
    NVIDIA_API_KEY: str
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    @field_validator(
        "PINECONE_API_KEY", "PINECONE_INDEX_NAME",
        "NVIDIA_API_KEY", "REDIS_HOST", "REDIS_PASSWORD",
        mode="before",
    )
    @classmethod
    def _strip_whitespace(cls, v: str) -> str:
        return v.strip()



# Single shared instance — imported by any module that needs config.
settings = Settings()
