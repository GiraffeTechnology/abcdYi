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

    # Test batch settings — allow bypassing human review in non-production environments
    SKIP_HUMAN_REVIEW: bool = False  # env var SKIP_HUMAN_REVIEW=true
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"

    def validate_skip_human_review(self):
        """Called at startup. Raises if production tries to skip review."""
        if self.SKIP_HUMAN_REVIEW and self.APP_ENV == "production":
            raise RuntimeError(
                "SKIP_HUMAN_REVIEW=true is not allowed in production. "
                "This setting is only for test/staging environments."
            )


settings = GPMSettings()
