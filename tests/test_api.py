"""SM Service Desk 领域测试：工单、评论、分派、状态流转、SLA。"""

import pytest
from fastapi.testclient import TestClient

from app import base
from app.main import VERSION, app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(base, "internal_api_key", lambda: "TEST")
    base.reset_state()
    from app.main import _init as init_db
    init_db()
    with TestClient(app) as c:
        c.headers["X-Internal-Token"] = "TEST"
        yield c


def _ticket(client, priority="P2"):
    return client.post("/api/desk/tickets", json={"title": "无法登录系统", "category": "账号", "priority": priority, "requester": "王五"}).json()["id"]


def test_health_and_version(client):
    r = client.get("/health", headers={"X-Request-Id": "suite-test"})
    assert r.status_code == 200
    assert r.json()["version"] == VERSION


def test_ticket_crud(client):
    ticket_id = _ticket(client)
    assert client.get("/api/desk/tickets").json()["total"] == 1
    detail = client.get(f"/api/desk/tickets/{ticket_id}").json()
    assert detail["status"] == "new"
    assert detail["sla_due_at"] is not None
    assert client.get("/api/desk/tickets/nope").status_code == 404


def test_comment_and_assign(client):
    ticket_id = _ticket(client)
    assert client.post(f"/api/desk/tickets/{ticket_id}/comments", json={"author": "王五", "content": "补充：连续 3 次失败"}).status_code == 201
    assert client.post(f"/api/desk/tickets/{ticket_id}/assign", json={"assignee": "赵工"}).json()["assignee"] == "赵工"
    detail = client.get(f"/api/desk/tickets/{ticket_id}").json()
    assert len(detail["comments"]) == 1
    assert detail["assignee"] == "赵工"


def test_status_flow(client):
    ticket_id = _ticket(client)
    assert client.post(f"/api/desk/tickets/{ticket_id}/status", json={"status": "open"}).json()["status"] == "open"
    assert client.post(f"/api/desk/tickets/{ticket_id}/status", json={"status": "resolved"}).json()["status"] == "resolved"


def test_filters(client):
    _ticket(client, priority="P1")
    _ticket(client, priority="P3")
    assert client.get("/api/desk/tickets", params={"priority": "P1"}).json()["total"] == 1
    assert client.get("/api/desk/tickets", params={"category": "账号"}).json()["total"] == 2


def test_sla_report(client):
    _ticket(client, priority="P1")
    report = client.get("/api/desk/sla").json()
    assert report["within_sla"] == 1
    assert report["breached"] == 0


def test_stats(client):
    _ticket(client)
    stats = client.get("/api/desk/stats").json()
    assert stats["total"] == 1
    assert stats["open"] == 1


def test_manifest_and_crypto(client):
    assert client.get("/api/integration/manifest").json()["version"] == VERSION
    enc = client.post("/api/crypto/encrypt", json={"value": "x"}).json()["ciphertext"]
    assert client.post("/api/crypto/decrypt", json={"value": enc}).json()["plaintext"] == "x"


def test_write_requires_auth(client):
    del client.headers["X-Internal-Token"]
    assert client.post("/api/desk/tickets", json={"title": "t", "category": "c", "requester": "r"}).status_code == 401
