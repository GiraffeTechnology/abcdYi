from pydantic_settings import BaseSettings


class GPMSettings(BaseSettings):
    GPM_DATABASE_URL: str = "postgresql+asyncpg://giraffe:giraffe@localhost:5432/apparel_textile"
    GPM_ALEMBIC_DATABASE_URL: str = "postgresql+psycopg2://giraffe:giraffe@localhost:5432/apparel_textile"
    GPM_API_KEY: str = "change-me-gpm-internal-key"
    GPM_HOST: str = "0.0.0.0"
    GPM_PORT: int = 8001

    # Deviation thresholds for auto-confirmation and exclusion
    # VALID (auto-confirm eligible): abs(deviation) <= threshold1
    # NEEDS_REVIEW (human review): threshold1 < abs(deviation) <= threshold2
    # EXCLUDED (reject): abs(deviation) > threshold2
    GPM_DEVIATION_THRESHOLD_VALID: float = 0.15
    GPM_DEVIATION_THRESHOLD_REVIEW: float = 0.40

    class Config:
        env_file = ".env"


settings = GPMSettings()
