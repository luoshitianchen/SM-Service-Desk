"""SLA 策略管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.sla import SLACreate, SLAUpdate
from app.services.sla import SLAService

router = APIRouter(prefix="/api/desk/slas", tags=["desk-slas"])


@router.get("")
async def list_slas(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    priority: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await SLAService.list_slas(session, limit=limit, offset=offset, priority=priority)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_sla(
    payload: SLACreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await SLAService.create_sla(session, payload, request)


@router.get("/{sla_id}")
async def get_sla(
    sla_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await SLAService.get_sla(session, sla_id)


@router.patch("/{sla_id}")
async def update_sla(
    sla_id: str, payload: SLAUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await SLAService.update_sla(session, sla_id, payload, request)
