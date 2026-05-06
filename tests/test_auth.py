"""
D1 smoke tests — register, login, /me, addresses, refresh.

Per the roadmap: smoke tests only at MVP. Full coverage is Phase 2.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_register_login_me_flow(client: AsyncClient, api_prefix: str):
    # Register
    r = await client.post(
        f"{api_prefix}/auth/register",
        json={
            "email": "Test@Example.com",  # mixed case to verify normalization
            "password": "supersecret123",
            "display_name": "Test User",
            "language": "en",
        },
    )
    assert r.status_code == 201, r.text
    tokens = r.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    access = tokens["access_token"]

    # /me with bearer
    r = await client.get(
        f"{api_prefix}/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == "test@example.com"
    assert me["display_name"] == "Test User"
    assert me["is_admin"] is False

    # Update profile
    r = await client.patch(
        f"{api_prefix}/me",
        headers={"Authorization": f"Bearer {access}"},
        json={"display_name": "Renamed", "default_city": "Riyadh"},
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == "Renamed"
    assert r.json()["default_city"] == "Riyadh"

    # Login again with same credentials
    r = await client.post(
        f"{api_prefix}/auth/login",
        json={"email": "test@example.com", "password": "supersecret123"},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(
    client: AsyncClient, api_prefix: str
):
    payload = {"email": "dup@example.com", "password": "supersecret123"}
    r = await client.post(f"{api_prefix}/auth/register", json=payload)
    assert r.status_code == 201
    r = await client.post(f"{api_prefix}/auth/register", json=payload)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_already_registered"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, api_prefix: str):
    await client.post(
        f"{api_prefix}/auth/register",
        json={"email": "u@example.com", "password": "rightpassword"},
    )
    r = await client.post(
        f"{api_prefix}/auth/login",
        json={"email": "u@example.com", "password": "wrongpassword"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient, api_prefix: str):
    r = await client.post(
        f"{api_prefix}/auth/register",
        json={"email": "r@example.com", "password": "supersecret123"},
    )
    refresh = r.json()["refresh_token"]

    r = await client.post(
        f"{api_prefix}/auth/refresh", json={"refresh_token": refresh}
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_address_crud(client: AsyncClient, api_prefix: str):
    r = await client.post(
        f"{api_prefix}/auth/register",
        json={"email": "addr@example.com", "password": "supersecret123"},
    )
    access = r.json()["access_token"]
    h = {"Authorization": f"Bearer {access}"}

    # Create
    r = await client.post(
        f"{api_prefix}/me/addresses",
        headers=h,
        json={
            "label": "Home",
            "address_line": "King Fahd Road, Building 5",
            "city": "Riyadh",
            "is_default": True,
        },
    )
    assert r.status_code == 201
    address_id = r.json()["id"]

    # List
    r = await client.get(f"{api_prefix}/me/addresses", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Update
    r = await client.patch(
        f"{api_prefix}/me/addresses/{address_id}",
        headers=h,
        json={"label": "Office"},
    )
    assert r.status_code == 200
    assert r.json()["label"] == "Office"

    # Delete
    r = await client.delete(f"{api_prefix}/me/addresses/{address_id}", headers=h)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth(client: AsyncClient, api_prefix: str):
    r = await client.get(f"{api_prefix}/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_request_does_not_leak_existence(
    client: AsyncClient, api_prefix: str
):
    """Reset endpoint returns the same response whether or not the email exists."""
    r1 = await client.post(
        f"{api_prefix}/auth/password/reset-request",
        json={"email": "doesnotexist@example.com"},
    )
    assert r1.status_code == 202

    await client.post(
        f"{api_prefix}/auth/register",
        json={"email": "real@example.com", "password": "supersecret123"},
    )
    r2 = await client.post(
        f"{api_prefix}/auth/password/reset-request",
        json={"email": "real@example.com"},
    )
    assert r2.status_code == 202
    assert r1.json() == r2.json()
