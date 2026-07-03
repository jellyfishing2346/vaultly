"""Current user profile and wallet."""

from fastapi import APIRouter, HTTPException

from app.core.deps import DB, CurrentUser
from app.models.schemas import AccountResponse, UserResponse

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserResponse)
async def me(db: DB, user_id: CurrentUser):
    row = await db.fetchrow(
        "SELECT id, email, handle, full_name FROM users WHERE id = $1", user_id
    )
    if row is None:
        raise HTTPException(404, "User not found")
    return UserResponse(**dict(row))


@router.get("/account", response_model=AccountResponse)
async def my_account(db: DB, user_id: CurrentUser):
    row = await db.fetchrow(
        """SELECT id, balance, currency FROM accounts
           WHERE user_id = $1 AND type = 'wallet'""",
        user_id,
    )
    if row is None:
        raise HTTPException(404, "Account not found")
    return AccountResponse(**dict(row))
