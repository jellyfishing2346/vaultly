"""Password hashing and JWT handling.

Note: we use the bcrypt library directly rather than passlib. passlib 1.7.4
is unmaintained and breaks with bcrypt >= 4.1 (it reads bcrypt.__about__,
which was removed). Direct bcrypt is simpler and future-proof.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID) -> str:
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None
