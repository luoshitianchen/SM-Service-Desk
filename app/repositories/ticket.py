"""工单仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket

# 工单状态机：合法的前置->后置迁移
TICKET_TRANSITIONS: dict[str, set[str]] = {
    "open": {"assigned"},
    "assigned": {"in_progress"},
    "in_progress": {"resolved"},
    "resolved": {"closed"},
    "closed": set(),
}


async def get_ticket(session: AsyncSession, ticket_id: str) -> Ticket | None:
    result = await session.execute(select(Ticket).where(Ticket.id == ticket_id))
    return result.scalar_one_or_none()


async def list_tickets(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    status: str | None = None,
    priority: str | None = None,
    keyword: str | None = None,
) -> list[Ticket]:
    stmt = select(Ticket).order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Ticket.status == status)
    if priority:
        stmt = stmt.where(Ticket.priority == priority)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Ticket.title.like(like), Ticket.requester.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_tickets(
    session: AsyncSession,
    status: str | None = None,
    priority: str | None = None,
    keyword: str | None = None,
) -> int:
    stmt = select(func.count(Ticket.id))
    if status:
        stmt = stmt.where(Ticket.status == status)
    if priority:
        stmt = stmt.where(Ticket.priority == priority)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Ticket.title.like(like), Ticket.requester.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_ticket(session: AsyncSession, ticket: Ticket) -> Ticket:
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket


async def update_ticket(session: AsyncSession, ticket: Ticket) -> Ticket:
    await session.commit()
    await session.refresh(ticket)
    return ticket
