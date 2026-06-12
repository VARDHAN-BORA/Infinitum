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
    GROQ_API_KEY: str
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379


# Single shared instance — imported by any module that needs config.
settings = Settings()
