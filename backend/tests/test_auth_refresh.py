"""Staying signed in: a refresh token buys a fresh pair until the account is
switched off (owner, 21-Oct-2026)."""

from app.auth.security import create_access_token, create_refresh_token, decode_token


def test_refresh_token_renews_the_sign_in(client, world, db):
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": create_refresh_token(str(world.admin.id))})
    assert res.status_code == 200, res.text
    body = res.json()
    assert decode_token(body["access_token"])["type"] == "access"
    assert decode_token(body["refresh_token"])["sub"] == str(world.admin.id)


def test_refresh_refuses_bad_tokens_and_inactive_users(client, world, db):
    # An access token is not a refresh token, and nonsense is nothing.
    for token in (create_access_token(str(world.admin.id)), "not-a-token"):
        assert client.post("/api/v1/auth/refresh", json={"refresh_token": token}).status_code == 401
    world.admin.is_active = False
    db.flush()
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": create_refresh_token(str(world.admin.id))})
    assert res.status_code == 401
