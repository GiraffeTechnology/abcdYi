import os
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./giraffe_mvp.db"
    DATABASE_ECHO: bool = False
    DB_MODE: str = "local_mvp"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = DatabaseSettings()
