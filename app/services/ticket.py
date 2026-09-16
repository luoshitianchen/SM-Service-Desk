"""工单服务层：状态机、SLA 时限计算与全生命周期管理。"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.ticket import Ticket
from app.repositories import sla as sla_repo
from app.repositories import ticket as repo
from app.repositories.ticket import TICKET_TRANSITIONS
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services.audit import record_audit


def _as_aware(dt: datetime | None) -> datetime | None:
    """SQLite 读回的时间可能为 naive，统一补齐为 UTC。"""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def compute_sla_status(due_at: datetime | None, now: datetime | None = None) -> dict:
    """根据承诺时限计算 SLA 执行状态（纯函数，便于单测）。"""
    if due_at is None:
        return {"due_at": None, "remaining_seconds": None, "overdue": False, "on_track": False}
    now = now or datetime.now(UTC)
    remaining = (_as_aware(due_at) - now).total_seconds()
    return {
        "due_at": _as_aware(due_at).isoformat(),
        "remaining_seconds": int(remaining),
        "overdue": remaining < 0,
        "on_track": remaining >= 0,
    }


def _ticket_to_dict(t: Ticket) -> dict:
    return {
        "id": t.id, "title": t.title, "description": t.description,
        "status": t.status, "priority": t.priority, "requester": t.requester,
        "assignee": t.assignee, "service_catalog_item_id": t.service_catalog_item_id,
        "sla_id": t.sla_id, "resolution": t.resolution,
        "due_at": t.due_at.isoformat() if t.due_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else "",
        "updated_at": t.updated_at.isoformat() if t.updated_at else "",
    }


class TicketService:
    @staticmethod
    async def list_tickets(
        session: AsyncSession, limit: int = 100, offset: int = 0,
        status_filter: str | None = None, priority_filter: str | None = None,
        keyword: str | None = None,
    ) -> dict:
        items = await repo.list_tickets(
            session, limit=limit, offset=offset, status=status_filter,
            priority=priority_filter, keyword=keyword,
        )
        total = await repo.count_tickets(session, status=status_filter, priority=priority_filter, keyword=keyword)
        return {"total": total, "items": [_ticket_to_dict(t) for t in items]}

    @staticmethod
    async def get_ticket(session: AsyncSession, ticket_id: str) -> dict:
        ticket = await repo.get_ticket(session, ticket_id)
        if not ticket:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "工单不存在")
        data = _ticket_to_dict(ticket)
        data["sla"] = compute_sla_status(ticket.due_at)
        return data

    @staticmethod
    async def _resolve_due_at(
        session: AsyncSession, payload: TicketCreate,
    ) -> tuple[str, datetime | None]:
        """确定工单适用的 SLA 并计算承诺解决时限。"""
        sla_id = payload.sla_id or ""
        # 未显式指定时，回退到服务目录项默认 SLA
        if not sla_id and payload.service_catalog_item_id:
            from app.repositories import service_catalog as catalog_repo
            item = await catalog_repo.get_item(session, payload.service_catalog_item_id)
            if item and item.sla_id:
                sla_id = item.sla_id
        sla: object = None
        if sla_id:
            sla = await sla_repo.get_sla(session, sla_id)
        else:
            # 再按优先级取一条启用中的 SLA
            sla = await sla_repo.get_sla_by_priority(session, payload.priority)
        if not sla:
            return "", None
        due = datetime.now(UTC) + timedelta(minutes=sla.resolution_minutes)
        return sla.id, due

    @staticmethod
    async def create_ticket(session: AsyncSession, payload: TicketCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        sla_id, due_at = await TicketService._resolve_due_at(session, payload)
        ticket = Ticket(
            id=str(uuid.uuid4()), title=payload.title, description=payload.description,
            status="open", priority=payload.priority, requester=payload.requester,
            assignee=payload.assignee or "",
            service_catalog_item_id=payload.service_catalog_item_id or "",
            sla_id=sla_id, due_at=due_at,
        )
        ticket = await repo.create_ticket(session, ticket)
        await record_audit(session, "ticket.created", "internal",
                           f"ticket_id={ticket.id} priority={payload.priority}", request)
        return _ticket_to_dict(ticket)

    @staticmethod
    async def update_ticket(session: AsyncSession, ticket_id: str, payload: TicketUpdate,
                            request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        ticket = await repo.get_ticket(session, ticket_id)
        if not ticket:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "工单不存在")
        if payload.title is not None:
            ticket.title = payload.title
        if payload.description is not None:
            ticket.description = payload.description
        if payload.priority is not None:
            ticket.priority = payload.priority
        if payload.assignee is not None:
            ticket.assignee = payload.assignee
        if payload.resolution is not None:
            ticket.resolution = payload.resolution
        ticket = await repo.update_ticket(session, ticket)
        await record_audit(session, "ticket.updated", "internal", f"ticket_id={ticket_id}", request)
        return _ticket_to_dict(ticket)

    @staticmethod
    async def change_status(session: AsyncSession, ticket_id: str, new_status: str,
                            request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        ticket = await repo.get_ticket(session, ticket_id)
        if not ticket:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "工单不存在")
        # 状态机校验：禁止跳跃或非法回退
        allowed_next = TICKET_TRANSITIONS.get(ticket.status, set())
        if new_status != ticket.status and new_status not in allowed_next:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"非法状态迁移：{ticket.status} -> {new_status}",
            )
        ticket.status = new_status
        ticket = await repo.update_ticket(session, ticket)
        await record_audit(session, "ticket.status_changed", "internal",
                           f"ticket_id={ticket_id} status={new_status}", request)
        return _ticket_to_dict(ticket)

    @staticmethod
    async def sla_status(session: AsyncSession, ticket_id: str) -> dict:
        ticket = await repo.get_ticket(session, ticket_id)
        if not ticket:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "工单不存在")
        return {"ticket_id": ticket_id, **compute_sla_status(ticket.due_at)}
