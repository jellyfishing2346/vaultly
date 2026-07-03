"""API integration tests. Requires docker compose services up.

Run: python -m pytest tests/test_api.py -v
"""

import uuid

import httpx
import pytest
from asgi_lifespan import LifespanManager

from app.main import app


@pytest.fixture
async def client():
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


def fresh_user():
    tag = uuid.uuid4().hex[:10]
    return {
        "email": f"{tag}@test.com",
        "handle": f"u_{tag}",
        "full_name": "Test User",
        "password": "hunter2hunter2",
    }


async def signup(client, user) -> dict:
    r = await client.post("/auth/signup", json=user)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_signup_login_and_balance(client):
    user = fresh_user()
    headers = await signup(client, user)

    r = await client.get("/me/account", headers=headers)
    assert r.status_code == 200
    assert r.json()["balance"] == 10_000  # welcome bonus

    r = await client.post(
        "/auth/login", json={"email": user["email"], "password": user["password"]}
    )
    assert r.status_code == 200

    r = await client.post(
        "/auth/login", json={"email": user["email"], "password": "wrong-password"}
    )
    assert r.status_code == 401


async def test_transfer_flow_and_idempotency(client):
    alice, bob = fresh_user(), fresh_user()
    alice_h = await signup(client, alice)
    bob_h = await signup(client, bob)

    key = f"test-{uuid.uuid4().hex}"
    payload = {"to_handle": bob["handle"], "amount": 2_500, "note": "lunch"}

    r1 = await client.post("/transfers", json=payload,
                           headers={**alice_h, "Idempotency-Key": key})
    assert r1.status_code == 201, r1.text
    assert r1.json()["replayed"] is False

    # Same key retried: no double charge.
    r2 = await client.post("/transfers", json=payload,
                           headers={**alice_h, "Idempotency-Key": key})
    assert r2.status_code == 201
    assert r2.json()["replayed"] is True
    assert r2.json()["id"] == r1.json()["id"]

    r = await client.get("/me/account", headers=alice_h)
    assert r.json()["balance"] == 7_500
    r = await client.get("/me/account", headers=bob_h)
    assert r.json()["balance"] == 12_500

    # Activity feed shows the transfer from both sides.
    r = await client.get("/transfers/activity", headers=bob_h)
    feed = r.json()
    assert feed[0]["direction"] == "received"
    assert feed[0]["counterparty_handle"] == alice["handle"]
    assert feed[0]["amount"] == 2_500


async def test_insufficient_funds_and_bad_recipient(client):
    alice = fresh_user()
    alice_h = await signup(client, alice)

    r = await client.post(
        "/transfers",
        json={"to_handle": "nobody_here_xyz", "amount": 100},
        headers={**alice_h, "Idempotency-Key": f"k-{uuid.uuid4().hex}"},
    )
    assert r.status_code == 404

    bob = fresh_user()
    await signup(client, bob)
    r = await client.post(
        "/transfers",
        json={"to_handle": bob["handle"], "amount": 999_999_999},
        headers={**alice_h, "Idempotency-Key": f"k-{uuid.uuid4().hex}"},
    )
    assert r.status_code == 422


async def test_auth_required(client):
    r = await client.get("/me/account")
    assert r.status_code == 401
