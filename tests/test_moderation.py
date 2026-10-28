from app import config
from tests.conftest import TAGS_A, TAGS_B


def test_block_hides_both_ways_and_closes_chat(client, pair, make_user):
    a, b = pair
    client.post(f"/api/chats/{b.id}/messages", json={"body": "привет"}, headers=a.h)
    assert client.post(f"/api/users/{b.id}/block", headers=a.h).json() == {"blocked": True}
    assert client.get("/api/matches", headers=b.h).json() == []
    assert client.post(f"/api/chats/{a.id}/messages", json={"body": "?"}, headers=b.h).status_code == 403
    c = make_user("C", TAGS_A)
    client.put("/api/profile", json={"tags": TAGS_A}, headers=b.h)
    assert a.id not in [x["id"] for x in client.get("/api/feed", headers=b.h).json()]
    assert c.id in [x["id"] for x in client.get("/api/feed", headers=b.h).json()]


def test_blocked_like_does_not_match(client, make_user):
    a, b = make_user("A", TAGS_A), make_user("B", TAGS_B)
    client.post("/api/swipe", json={"target": b.id, "liked": True}, headers=a.h)
    client.post(f"/api/users/{a.id}/block", headers=b.h)
    assert client.post("/api/swipe", json={"target": a.id, "liked": True}, headers=b.h).json() == {"match": False}


def test_reports_auto_hide_then_admin_bans(client, make_user):
    bad = make_user("Спамер", TAGS_B)
    viewer = make_user("Зритель", TAGS_A)
    reporters = [make_user(f"R{i}", TAGS_A) for i in range(config.REPORTS_TO_HIDE)]
    assert bad.id in [x["id"] for x in client.get("/api/feed", headers=viewer.h).json()]
    for r in reporters:
        assert client.post(f"/api/users/{bad.id}/report", json={"reason": "spam", "comment": "реклама"},
                           headers=r.h).status_code == 200
    assert bad.id not in [x["id"] for x in client.get("/api/feed", headers=viewer.h).json()]

    admin = make_user("Admin", role="admin")
    assert client.get("/api/admin/reports", headers=viewer.h).status_code == 403
    reps = client.get("/api/admin/reports", headers=admin.h).json()
    assert len(reps) == config.REPORTS_TO_HIDE and reps[0]["target"] == bad.id and reps[0]["hidden_at"]

    assert client.post(f"/api/admin/reports/{reps[0]['id']}", json={"action": "ban"}, headers=admin.h).status_code == 200
    assert client.get("/api/admin/reports", headers=admin.h).json() == []
    assert len(client.get("/api/admin/reports?status=actioned", headers=admin.h).json()) == config.REPORTS_TO_HIDE
    assert client.post("/api/login", json={"email": bad.email, "password": "password123"}).status_code == 403
    assert client.get("/api/me", headers=bad.h).json()["detail"] == "banned"

    client.post(f"/api/admin/users/{bad.id}/unban", headers=admin.h)
    assert client.post("/api/login", json={"email": bad.email, "password": "password123"}).status_code == 200


def test_dismiss_unhides(client, make_user):
    bad = make_user("B", TAGS_B)
    reps = [make_user(f"R{i}", TAGS_A) for i in range(config.REPORTS_TO_HIDE)]
    for r in reps:
        client.post(f"/api/users/{bad.id}/report", json={"reason": "fake"}, headers=r.h)
    admin = make_user("Admin", role="admin")
    first = client.get("/api/admin/reports", headers=admin.h).json()[0]
    client.post(f"/api/admin/reports/{first['id']}", json={"action": "dismiss"}, headers=admin.h)
    viewer = make_user("V", TAGS_A)
    assert bad.id in [x["id"] for x in client.get("/api/feed", headers=viewer.h).json()]


def test_report_validation_and_duplicates(client, make_user):
    a, b = make_user("A", TAGS_A), make_user("B", TAGS_B)
    assert client.post(f"/api/users/{b.id}/report", json={"reason": "meh"}, headers=a.h).status_code == 422
    for _ in range(2):
        assert client.post(f"/api/users/{b.id}/report", json={"reason": "spam"}, headers=a.h).status_code == 200
    admin = make_user("Admin", role="admin")
    assert len(client.get("/api/admin/reports", headers=admin.h).json()) == 1


def test_admin_can_delete_photo(client, make_user):
    import io
    from PIL import Image
    b = make_user("B")
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "PNG")
    pid = client.post("/api/photos", files={"file": ("x.png", buf.getvalue())}, headers=b.h).json()[0]["id"]
    admin = make_user("Admin", role="admin")
    assert client.delete(f"/api/admin/photos/{pid}", headers=b.h).status_code == 403
    assert client.delete(f"/api/admin/photos/{pid}", headers=admin.h).status_code == 200
    assert client.get("/api/me", headers=b.h).json()["photos"] == []
