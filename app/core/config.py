from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AgentVerse Search"
    APP_VERSION: str = "1.0.0"
    DATABASE_URL: str = "sqlite+aiosqlite:///./agentverse.db"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
