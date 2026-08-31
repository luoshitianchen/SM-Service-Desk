"""SM Service Desk —— 服务台：工单、分类、分派、SLA 与闭环。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from app import base

SERVICE = "sm-service-desk"
VERSION = "2.0.0"
NAME = "SM Service Desk"
DESCRIPTION = "服务台：工单、分类、分派、SLA 与闭环"
PORT = 8370

SLA_HOURS = {"P1": 4, "P2": 24, "P3": 72, "P4": 168}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _init() -> None:
    with base.db_ctx() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
                category TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'P3',
                status TEXT NOT NULL DEFAULT 'new', requester TEXT NOT NULL,
                assignee TEXT, sla_due_at TEXT, created_at TEXT NOT NULL, resolved_at TEXT
            );
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL, author TEXT NOT NULL,
                content TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status, priority);
            """
        )


app = base.create_app(
    service=SERVICE, name=NAME, description=DESCRIPTION, version=VERSION, port=PORT,
    dependencies=["sm-iam", "sm-workflow-approval", "sm-audit-log-center"],
    events=["ticket.created", "ticket.assigned", "ticket.resolved", "ticket.sla_breached"],
    overview_fn=lambda _r: {
        "summary": {
            "open": base.get_db().execute("SELECT COUNT(*) FROM tickets WHERE status NOT IN ('resolved','closed')").fetchone()[0],
            "sla_breached": base.get_db().execute("SELECT COUNT(*) FROM tickets WHERE status NOT IN ('resolved','closed') AND sla_due_at<datetime('now')").fetchone()[0],
        }
    },
)
_init()


class TicketIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    category: str = Field(min_length=2, max_length=60)
    priority: str = Field(default="P3", pattern=r"^(P1|P2|P3|P4)$")
    requester: str = Field(min_length=1, max_length=80)


class CommentIn(BaseModel):
    author: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=2000)


class AssignIn(BaseModel):
    assignee: str = Field(min_length=1, max_length=80)


class StatusIn(BaseModel):
    status: str = Field(pattern=r"^(new|open|pending|resolved|closed)$")


@app.post("/api/desk/tickets", status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    ticket_id = str(uuid.uuid4())
    sla_hours = SLA_HOURS.get(payload.priority, 72)
    sla_due_at = (datetime.now(UTC) + timedelta(hours=sla_hours)).isoformat()
    with base.db_ctx() as conn:
        conn.execute("INSERT INTO tickets (id, title, description, category, priority, status, requester, assignee, sla_due_at, created_at, resolved_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (ticket_id, payload.title, payload.description, payload.category, payload.priority, "new", payload.requester, None, sla_due_at, _now(), None))
        base.record_audit("ticket.created", payload.requester, f"ticket={ticket_id} priority={payload.priority}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": ticket_id, "title": payload.title, "sla_due_at": sla_due_at, "status": "new"}


@app.get("/api/desk/tickets")
def list_tickets(status_: str | None = None, priority: str | None = None, category: str | None = None) -> dict[str, Any]:
    clauses, params = [], []
    if status_:
        clauses.append("status=?")
        params.append(status_)
    if priority:
        clauses.append("priority=?")
        params.append(priority)
    if category:
        clauses.append("category=?")
        params.append(category)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with base.db_ctx() as conn:
        rows = conn.execute(f"SELECT * FROM tickets{where} ORDER BY CASE priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 ELSE 4 END, created_at DESC LIMIT 200", params).fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.get("/api/desk/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict[str, Any]:
    with base.db_ctx() as conn:
        ticket = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if not ticket:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "工单不存在")
        comments = conn.execute("SELECT * FROM comments WHERE ticket_id=? ORDER BY created_at ASC", (ticket_id,)).fetchall()
    return {**dict(ticket), "comments": [dict(r) for r in comments]}


@app.post("/api/desk/tickets/{ticket_id}/comments", status_code=status.HTTP_201_CREATED)
def add_comment(ticket_id: str, payload: CommentIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    comment_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        if not conn.execute("SELECT 1 FROM tickets WHERE id=?", (ticket_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "工单不存在")
        conn.execute("INSERT INTO comments VALUES (?,?,?,?,?)", (comment_id, ticket_id, payload.author, payload.content, _now()))
    return {"id": comment_id, "ticket_id": ticket_id}


@app.post("/api/desk/tickets/{ticket_id}/assign")
def assign_ticket(ticket_id: str, payload: AssignIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    with base.db_ctx() as conn:
        if conn.execute("UPDATE tickets SET assignee=?, status=CASE WHEN status='new' THEN 'open' ELSE status END WHERE id=?", (payload.assignee, ticket_id)).rowcount == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "工单不存在")
        base.record_audit("ticket.assigned", "internal", f"ticket={ticket_id} assignee={payload.assignee}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": ticket_id, "assignee": payload.assignee}


@app.post("/api/desk/tickets/{ticket_id}/status")
def set_status(ticket_id: str, payload: StatusIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    with base.db_ctx() as conn:
        resolved_at = _now() if payload.status == "resolved" else None
        if conn.execute("UPDATE tickets SET status=?, resolved_at=CASE WHEN ?='resolved' THEN ? ELSE resolved_at END WHERE id=?", (payload.status, payload.status, resolved_at, ticket_id)).rowcount == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "工单不存在")
        base.record_audit("ticket.resolved", "internal", f"ticket={ticket_id} status={payload.status}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": ticket_id, "status": payload.status}


@app.get("/api/desk/sla")
def sla_report() -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM tickets WHERE status NOT IN ('resolved','closed')").fetchall()
    breached = [dict(r) for r in rows if r["sla_due_at"] and r["sla_due_at"] < _now()]
    return {"within_sla": len(rows) - len(breached), "breached": len(breached), "breached_tickets": breached}


@app.get("/api/desk/stats")
def stats() -> dict[str, Any]:
    with base.db_ctx() as conn:
        def _count(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]
        by_status = [dict(r) for r in conn.execute("SELECT status, COUNT(*) AS count FROM tickets GROUP BY status").fetchall()]
        return {
            "total": _count("SELECT COUNT(*) FROM tickets"),
            "open": _count("SELECT COUNT(*) FROM tickets WHERE status NOT IN ('resolved','closed')"),
            "resolved": _count("SELECT COUNT(*) FROM tickets WHERE status='resolved'"),
            "p1": _count("SELECT COUNT(*) FROM tickets WHERE priority='P1' AND status NOT IN ('resolved','closed')"),
            "by_status": by_status,
        }
