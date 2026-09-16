"""Service-Desk 业务深化测试：工单状态机 / 服务目录 / SLA 时限。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ticket import compute_sla_status

INTERNAL_TOKEN = "test-internal-key-12345"
AUTH_HEADERS = {"X-Internal-Token": INTERNAL_TOKEN}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════
# SLA 策略
# ═══════════════════════════════════════════════════════════
class TestSLAManagement:
    def test_create_sla_success(self, client):
        resp = client.post("/api/desk/slas", json={
            "name": "高级优先级 SLA", "priority": "high",
            "response_minutes": 15, "resolution_minutes": 120,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "高级优先级 SLA"
        assert data["resolution_minutes"] == 120
        assert data["is_active"] is True
        assert "id" in data

    def test_create_sla_requires_token(self, client):
        resp = client.post("/api/desk/slas", json={"name": "无令牌 SLA"})
        assert resp.status_code in (401, 403)

    def test_list_slas(self, client):
        resp = client.get("/api/desk/slas", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_slas_filter_priority(self, client):
        resp = client.get("/api/desk/slas?priority=high", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["priority"] == "high"

    def test_get_sla_not_found(self, client):
        resp = client.get("/api/desk/slas/nonexistent-id", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_update_sla(self, client):
        list_resp = client.get("/api/desk/slas", headers=AUTH_HEADERS)
        sla_id = list_resp.json()["items"][0]["id"]
        resp = client.patch(f"/api/desk/slas/{sla_id}", json={
            "resolution_minutes": 60, "is_active": False,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["resolution_minutes"] == 60
        assert resp.json()["is_active"] is False


# ═══════════════════════════════════════════════════════════
# 服务目录
# ═══════════════════════════════════════════════════════════
class TestCatalogManagement:
    def test_create_catalog_item_success(self, client):
        list_resp = client.get("/api/desk/slas", headers=AUTH_HEADERS)
        sla_id = list_resp.json()["items"][0]["id"]
        resp = client.post("/api/desk/catalog-items", json={
            "name": "账号开通", "code": "CAT-ACC-001", "category": "账号",
            "description": "新员工账号开通", "sla_id": sla_id,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "CAT-ACC-001"
        assert data["sla_id"] == sla_id

    def test_create_catalog_duplicate_code(self, client):
        resp = client.post("/api/desk/catalog-items", json={
            "name": "重复", "code": "CAT-ACC-001",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_create_catalog_requires_token(self, client):
        resp = client.post("/api/desk/catalog-items", json={
            "name": "无令牌", "code": "CAT-NONE",
        })
        assert resp.status_code in (401, 403)

    def test_list_catalog(self, client):
        resp = client.get("/api/desk/catalog-items", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_catalog_keyword(self, client):
        resp = client.get("/api/desk/catalog-items?keyword=账号", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1

    def test_update_catalog(self, client):
        list_resp = client.get("/api/desk/catalog-items", headers=AUTH_HEADERS)
        item_id = list_resp.json()["items"][0]["id"]
        resp = client.patch(f"/api/desk/catalog-items/{item_id}", json={
            "description": "更新后的描述", "is_active": False,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["description"] == "更新后的描述"
        assert resp.json()["is_active"] is False

    def test_delete_catalog(self, client):
        client.post("/api/desk/catalog-items", json={
            "name": "待删除项", "code": "CAT-DEL-001",
        }, headers=AUTH_HEADERS)
        list_resp = client.get("/api/desk/catalog-items?keyword=待删除项", headers=AUTH_HEADERS)
        item = list_resp.json()["items"][0]
        resp = client.delete(f"/api/desk/catalog-items/{item['id']}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════════════════
# 工单与状态机
# ═══════════════════════════════════════════════════════════
class TestTicketWorkflow:
    def _get_catalog_item_id(self, client) -> str:
        list_resp = client.get("/api/desk/catalog-items?keyword=账号开通", headers=AUTH_HEADERS)
        items = list_resp.json()["items"]
        return items[0]["id"]

    def test_create_ticket_success(self, client):
        item_id = self._get_catalog_item_id(client)
        resp = client.post("/api/desk/tickets", json={
            "title": "VPN 无法连接", "description": "出差场景连不上 VPN",
            "priority": "high", "requester": "zhangsan",
            "service_catalog_item_id": item_id,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "open"
        assert data["priority"] == "high"
        # 引用目录项后应继承其 SLA
        assert data["sla_id"] != ""
        assert data["due_at"] is not None

    def test_create_ticket_requires_token(self, client):
        resp = client.post("/api/desk/tickets", json={
            "title": "无令牌工单", "requester": "lisi",
        })
        assert resp.status_code in (401, 403)

    def test_create_ticket_without_sla(self, client):
        resp = client.post("/api/desk/tickets", json={
            "title": "普通咨询工单", "priority": "low", "requester": "wangwu",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert data["sla_id"] == ""
        assert data["due_at"] is None

    def test_list_and_filter_tickets(self, client):
        resp = client.get("/api/desk/tickets?status=open", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["status"] == "open"

    def test_filter_by_priority(self, client):
        resp = client.get("/api/desk/tickets?priority=high", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["priority"] == "high"

    def test_keyword_search(self, client):
        resp = client.get("/api/desk/tickets?keyword=VPN", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        titles = [t["title"] for t in resp.json()["items"]]
        assert any("VPN" in t for t in titles)

    def test_get_ticket_and_sla_endpoint(self, client):
        list_resp = client.get("/api/desk/tickets?keyword=VPN", headers=AUTH_HEADERS)
        ticket_id = list_resp.json()["items"][0]["id"]
        resp = client.get(f"/api/desk/tickets/{ticket_id}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["sla"]["on_track"] is True
        sla_resp = client.get(f"/api/desk/tickets/{ticket_id}/sla", headers=AUTH_HEADERS)
        assert sla_resp.status_code == 200
        assert sla_resp.json()["overdue"] is False

    def test_get_ticket_not_found(self, client):
        resp = client.get("/api/desk/tickets/nonexistent-id", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_full_status_machine(self, client):
        list_resp = client.get("/api/desk/tickets?keyword=VPN", headers=AUTH_HEADERS)
        ticket_id = list_resp.json()["items"][0]["id"]
        # open -> assigned
        r = client.patch(f"/api/desk/tickets/{ticket_id}/status",
                         json={"status": "assigned"}, headers=AUTH_HEADERS)
        assert r.status_code == 200 and r.json()["status"] == "assigned"
        # assigned -> in_progress
        r = client.patch(f"/api/desk/tickets/{ticket_id}/status",
                         json={"status": "in_progress"}, headers=AUTH_HEADERS)
        assert r.status_code == 200 and r.json()["status"] == "in_progress"
        # in_progress -> resolved
        r = client.patch(f"/api/desk/tickets/{ticket_id}/status",
                         json={"status": "resolved"}, headers=AUTH_HEADERS)
        assert r.status_code == 200 and r.json()["status"] == "resolved"
        # resolved -> closed
        r = client.patch(f"/api/desk/tickets/{ticket_id}/status",
                         json={"status": "closed"}, headers=AUTH_HEADERS)
        assert r.status_code == 200 and r.json()["status"] == "closed"

    def test_illegal_transition_rejected(self, client):
        list_resp = client.get("/api/desk/tickets?keyword=VPN", headers=AUTH_HEADERS)
        ticket_id = list_resp.json()["items"][0]["id"]
        # 已 closed，禁止再迁移
        resp = client.patch(f"/api/desk/tickets/{ticket_id}/status",
                            json={"status": "open"}, headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_invalid_jump_rejected(self, client):
        resp = client.post("/api/desk/tickets", json={
            "title": "跳跃测试工单", "requester": "zhaoliu",
        }, headers=AUTH_HEADERS)
        ticket_id = resp.json()["id"]
        # open 不能直接到 resolved
        bad = client.patch(f"/api/desk/tickets/{ticket_id}/status",
                           json={"status": "resolved"}, headers=AUTH_HEADERS)
        assert bad.status_code == 409

    def test_update_ticket(self, client):
        list_resp = client.get("/api/desk/tickets?keyword=普通咨询", headers=AUTH_HEADERS)
        ticket_id = list_resp.json()["items"][0]["id"]
        resp = client.patch(f"/api/desk/tickets/{ticket_id}", json={
            "assignee": "ops-team", "resolution": "已答复",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["assignee"] == "ops-team"
        assert resp.json()["resolution"] == "已答复"


# ═══════════════════════════════════════════════════════════
# SLA 超时计算（纯函数确定性测试）
# ═══════════════════════════════════════════════════════════
class TestSLAComputation:
    def test_sla_no_due_at(self):
        result = compute_sla_status(None)
        assert result["overdue"] is False
        assert result["on_track"] is False

    def test_sla_not_overdue(self):
        future = datetime.now(UTC) + timedelta(minutes=30)
        result = compute_sla_status(future)
        assert result["overdue"] is False
        assert result["on_track"] is True
        assert result["remaining_seconds"] > 0

    def test_sla_overdue(self):
        past = datetime.now(UTC) - timedelta(minutes=10)
        result = compute_sla_status(past)
        assert result["overdue"] is True
        assert result["on_track"] is False
        assert result["remaining_seconds"] < 0
