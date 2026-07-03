"""Request/response schemas. Amounts are always integer cents at the API
boundary — the frontend formats them for display. Floats never touch money."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    handle: str = Field(min_length=3, max_length=30, pattern=r"^[a-z0-9_]+$")
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    handle: str
    full_name: str


class AccountResponse(BaseModel):
    id: uuid.UUID
    balance: int  # cents
    currency: str


class TransferRequest(BaseModel):
    to_handle: str
    amount: int = Field(gt=0, description="Amount in cents")
    note: str | None = Field(default=None, max_length=280)


class TransferResponse(BaseModel):
    id: uuid.UUID
    status: str
    amount: int
    note: str | None
    replayed: bool = False


class ActivityItem(BaseModel):
    id: uuid.UUID
    direction: str  # "sent" | "received"
    counterparty_handle: str
    counterparty_name: str
    amount: int
    note: str | None
    status: str
    created_at: datetime
