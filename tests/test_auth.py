from app import mailer
from app.db import pool
from app.security import make_token
from tests.conftest import TAGS_A, verify_link_for


def test_register_without_location_and_login(client):
    r = client.post("/api/register", json={"email": "Ann@Test.dev", "password": "password123", "name": "Анна", "age": 25})
    assert r.status_code == 200
    r = client.post("/api/login", json={"email": "ann@test.dev", "password": "password123"})
    assert r.status_code == 200 and r.json()["token"]


def test_duplicate_and_bad_credentials(client, make_user):
    u = make_user()
    r = client.post("/api/register", json={"email": u.email, "password": "password123", "name": "X", "age": 30})
    assert r.status_code == 409
    assert client.post("/api/login", json={"email": u.email, "password": "wrongpass1"}).status_code == 401
    assert client.post("/api/register", json={"email": "kid@test.dev", "password": "password123",
                                              "name": "X", "age": 16}).status_code == 422


def test_email_verification_flow(client, make_user):
    u = make_user(verify=False, tags=TAGS_A)
    me = client.get("/api/me", headers=u.h).json()
    assert me["email_verified"] is False and me["has_profile"] is True
    assert client.get("/api/feed", headers=u.h).json()["detail"] == "email_unverified"

    assert client.post("/api/resend-verification", headers=u.h).json() == {"sent": True}
    r = client.get(verify_link_for(u.email), follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/#verified"
    assert client.get("/api/me", headers=u.h).json()["email_verified"] is True
    assert client.get("/api/feed", headers=u.h).status_code == 200


def test_verification_rejects_forged_or_wrong_type_tokens(client, make_user):
    u = make_user(verify=False)
    r = client.get(f"/api/verify-email?token={u.token}", follow_redirects=False)
    assert r.headers["location"] == "/#verify-failed"
    other = make_token(u.id, typ="verify", email="someone@else.dev")
    client.get(f"/api/verify-email?token={other}", follow_redirects=False)
    assert client.get("/api/me", headers=u.h).json()["email_verified"] is False


def test_verify_token_cannot_be_used_as_access(client, make_user):
    u = make_user(verify=False)
    tok = make_token(u.id, typ="verify", email=u.email)
    assert client.get("/api/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_verification_mail_content(client, make_user):
    u = make_user(verify=False)
    msg = mailer.outbox[-1]
    assert msg["To"] == u.email and "Подтвердите" in msg["Subject"]


def test_login_rate_limit(client, make_user):
    u = make_user()
    codes = [client.post("/api/login", json={"email": u.email, "password": "wrongpass1"}).status_code
             for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429


def test_no_geo_columns_left(client):
    with pool.connection() as c:
        cols = {r["column_name"] for r in c.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='users'").fetchall()}
    assert not {"lat", "lon"} & cols
