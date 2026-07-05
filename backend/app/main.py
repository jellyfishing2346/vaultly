"""vaultly API entrypoint.

Run:  uvicorn app.main:app --reload
Docs: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, me, transfers
from app.core.deps import close_pools, create_pools


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pools(app)
    yield
    await close_pools(app)


app = FastAPI(title="vaultly", version="0.2.0", lifespan=lifespan)

import os

_default_origins = "http://localhost:3000"
allow_origins = os.getenv("CORS_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(transfers.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
