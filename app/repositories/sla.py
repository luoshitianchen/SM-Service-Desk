"""SLA 策略仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sla_policy import SLAPolicy


async def get_sla(session: AsyncSession, sla_id: str) -> SLAPolicy | None:
    result = await session.execute(select(SLAPolicy).where(SLAPolicy.id == sla_id))
    return result.scalar_one_or_none()


async def get_sla_by_priority(session: AsyncSession, priority: str) -> SLAPolicy | None:
    """按优先级取一条启用中的 SLA 策略。"""
    result = await session.execute(
        select(SLAPolicy)
        .where(SLAPolicy.priority == priority, SLAPolicy.is_active.is_(True))
        .order_by(SLAPolicy.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_slas(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    priority: str | None = None,
) -> list[SLAPolicy]:
    stmt = select(SLAPolicy).order_by(SLAPolicy.created_at.desc()).limit(limit).offset(offset)
    if priority:
        stmt = stmt.where(SLAPolicy.priority == priority)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_slas(session: AsyncSession, priority: str | None = None) -> int:
    stmt = select(func.count(SLAPolicy.id))
    if priority:
        stmt = stmt.where(SLAPolicy.priority == priority)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_sla(session: AsyncSession, sla: SLAPolicy) -> SLAPolicy:
    session.add(sla)
    await session.commit()
    await session.refresh(sla)
    return sla


async def update_sla(session: AsyncSession, sla: SLAPolicy) -> SLAPolicy:
    await session.commit()
    await session.refresh(sla)
    return sla
