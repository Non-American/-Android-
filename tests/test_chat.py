import pytest
from starlette.websockets import WebSocketDisconnect

from tests.conftest import TAGS_A, TAGS_C


def test_chat_requires_match(client, make_user):
    a, b = make_user("A", TAGS_A), make_user("B", TAGS_C)
    assert client.post(f"/api/chats/{b.id}/messages", json={"body": "привет"}, headers=a.h).status_code == 403
    assert client.get(f"/api/chats/{b.id}/messages", headers=a.h).status_code == 403


def test_send_history_unread_and_read(client, pair):
    a, b = pair
    for text in ("привет", "как дела?"):
        r = client.post(f"/api/chats/{b.id}/messages", json={"body": text}, headers=a.h)
        assert r.status_code == 200 and r.json()["sender"] == a.id
    m = client.get("/api/matches", headers=b.h).json()[0]
    assert m["id"] == a.id and m["unread"] == 2 and m["last_body"] == "как дела?"
    hist = client.get(f"/api/chats/{a.id}/messages", headers=b.h).json()
    assert [x["body"] for x in hist] == ["привет", "как дела?"]
    assert client.get("/api/matches", headers=b.h).json()[0]["unread"] == 0
    assert all(x["read_at"] for x in client.get(f"/api/chats/{b.id}/messages", headers=a.h).json())


def test_history_pagination(client, pair):
    a, b = pair
    ids = [client.post(f"/api/chats/{b.id}/messages", json={"body": str(i)}, headers=a.h).json()["id"]
           for i in range(5)]
    page = client.get(f"/api/chats/{b.id}/messages?limit=2", headers=a.h).json()
    assert [x["id"] for x in page] == ids[-2:]
    older = client.get(f"/api/chats/{b.id}/messages?limit=2&before={page[0]['id']}", headers=a.h).json()
    assert [x["id"] for x in older] == ids[1:3]


def test_message_validation(client, pair):
    a, b = pair
    assert client.post(f"/api/chats/{b.id}/messages", json={"body": "x" * 2001}, headers=a.h).status_code == 422
    assert client.post(f"/api/chats/{b.id}/messages", json={"body": "   "}, headers=a.h).status_code == 422


def test_message_rate_limit(client, pair):
    a, b = pair
    codes = [client.post(f"/api/chats/{b.id}/messages", json={"body": "spam"}, headers=a.h).status_code
             for _ in range(31)]
    assert codes[-1] == 429 and codes[:30] == [200] * 30


def test_websocket_delivers_messages(client, pair):
    a, b = pair
    with client.websocket_connect("/api/ws") as ws:
        ws.send_text(b.token)
        assert ws.receive_json() == {"type": "ready"}
        client.post(f"/api/chats/{b.id}/messages", json={"body": "живое"}, headers=a.h)
        ev = ws.receive_json()
        assert ev["type"] == "message" and ev["chat"] == a.id and ev["message"]["body"] == "живое"


def test_websocket_match_event(client, make_user):
    a, b = make_user("A", TAGS_A), make_user("B", TAGS_C)
    client.post("/api/swipe", json={"target": b.id, "liked": True}, headers=a.h)
    with client.websocket_connect("/api/ws") as ws:
        ws.send_text(a.token)
        ws.receive_json()
        client.post("/api/swipe", json={"target": a.id, "liked": True}, headers=b.h)
        ev = ws.receive_json()
        assert ev["type"] == "match" and ev["user"]["id"] == b.id


def test_websocket_rejects_bad_token(client):
    with client.websocket_connect("/api/ws") as ws:
        ws.send_text("not-a-token")
        with pytest.raises(WebSocketDisconnect) as e:
            ws.receive_json()
    assert e.value.code == 4401


def test_hub_fans_out_to_every_socket_of_user(client, pair):
    a, b = pair
    with client.websocket_connect("/api/ws") as w1, client.websocket_connect("/api/ws") as w2:
        for w in (w1, w2):
            w.send_text(b.token)
            assert w.receive_json() == {"type": "ready"}
        client.post(f"/api/chats/{b.id}/messages", json={"body": "обоим"}, headers=a.h)
        assert w1.receive_json()["message"]["body"] == "обоим"
        assert w2.receive_json()["message"]["body"] == "обоим"
    with client.websocket_connect("/api/ws") as w3:
        w3.send_text(b.token)
        w3.receive_json()
        client.post(f"/api/chats/{b.id}/messages", json={"body": "снова"}, headers=a.h)
        assert w3.receive_json()["message"]["body"] == "снова"
