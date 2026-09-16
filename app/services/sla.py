"""SLA 策略服务层。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.sla_policy import SLAPolicy
from app.repositories import sla as repo
from app.schemas.sla import SLACreate, SLAUpdate
from app.services.audit import record_audit


def _sla_to_dict(s: SLAPolicy) -> dict:
    return {
        "id": s.id, "name": s.name, "priority": s.priority,
        "response_minutes": s.response_minutes, "resolution_minutes": s.resolution_minutes,
        "is_active": s.is_active,
        "created_at": s.created_at.isoformat() if s.created_at else "",
    }


class SLAService:
    @staticmethod
    async def list_slas(session: AsyncSession, limit: int = 100, offset: int = 0,
                        priority: str | None = None) -> dict:
        items = await repo.list_slas(session, limit=limit, offset=offset, priority=priority)
        total = await repo.count_slas(session, priority=priority)
        return {"total": total, "items": [_sla_to_dict(s) for s in items]}

    @staticmethod
    async def get_sla(session: AsyncSession, sla_id: str) -> dict:
        sla = await repo.get_sla(session, sla_id)
        if not sla:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "SLA 策略不存在")
        return _sla_to_dict(sla)

    @staticmethod
    async def create_sla(session: AsyncSession, payload: SLACreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        sla = SLAPolicy(
            id=str(uuid.uuid4()), name=payload.name, priority=payload.priority,
            response_minutes=payload.response_minutes,
            resolution_minutes=payload.resolution_minutes, is_active=True,
        )
        sla = await repo.create_sla(session, sla)
        await record_audit(session, "sla.created", "internal", f"sla_id={sla.id}", request)
        return _sla_to_dict(sla)

    @staticmethod
    async def update_sla(session: AsyncSession, sla_id: str, payload: SLAUpdate,
                         request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        sla = await repo.get_sla(session, sla_id)
        if not sla:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "SLA 策略不存在")
        if payload.name is not None:
            sla.name = payload.name
        if payload.response_minutes is not None:
            sla.response_minutes = payload.response_minutes
        if payload.resolution_minutes is not None:
            sla.resolution_minutes = payload.resolution_minutes
        if payload.is_active is not None:
            sla.is_active = payload.is_active
        sla = await repo.update_sla(session, sla)
        await record_audit(session, "sla.updated", "internal", f"sla_id={sla_id}", request)
        return _sla_to_dict(sla)
