"""Connection pools and FastAPI dependencies."""

import uuid
from typing import Annotated

import asyncpg
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


async def create_pools(app):
    app.state.db = await asyncpg.create_pool(
        settings.DATABASE_DSN, min_size=5, max_size=20
    )
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_pools(app):
    await app.state.db.close()
    await app.state.redis.aclose()


def get_db(request: Request) -> asyncpg.Pool:
    return request.app.state.db


def get_redis(request: Request):
    return request.app.state.redis


async def get_current_user_id(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> uuid.UUID:
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id


DB = Annotated[asyncpg.Pool, Depends(get_db)]
Redis = Annotated[object, Depends(get_redis)]
CurrentUser = Annotated[uuid.UUID, Depends(get_current_user_id)]
