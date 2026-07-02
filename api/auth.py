from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from src.db.base import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Known weak placeholder values that must never sign real JWTs.
WEAK_SECRET_PLACEHOLDERS = {
    "change-me-in-production",
    "change-me-in-production-use-long-random-string",
}
MIN_SECRET_KEY_LENGTH = 32


def validate_secret_key(secret: Optional[str]) -> None:
    """Fail-fast if the JWT signing key is unset, a known placeholder, or too short.

    HS256 tokens are forgeable by anyone who knows the key, so a predictable or
    short key is equivalent to having no authentication at all. The API must
    refuse to start rather than silently sign tokens with a guessable secret.
    """
    if (
        not secret
        or secret.strip() in WEAK_SECRET_PLACEHOLDERS
        or len(secret) < MIN_SECRET_KEY_LENGTH
    ):
        raise RuntimeError(
            "Insecure SECRET_KEY: it is unset, a known placeholder, or shorter "
            f"than {MIN_SECRET_KEY_LENGTH} characters. Set SECRET_KEY to a long "
            "random string before starting the API (see .env.example)."
        )


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(
        {"sub": subject, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
