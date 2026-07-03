"""App settings. Env vars override defaults; defaults match docker-compose ports."""

import os


class Settings:
    DATABASE_DSN: str = os.getenv(
        "DATABASE_DSN", 
        os.getenv("DATABASE_URL", "postgresql://vaultly:vaultly_dev@localhost:5433/vaultly")
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")
    JWT_SECRET: str = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "dev-secret-change-in-production"))
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h for dev convenience
    RATE_LIMIT_TRANSFERS_PER_MINUTE: int = 10


settings = Settings()
