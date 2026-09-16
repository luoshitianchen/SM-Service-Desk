"""工单管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.ticket import TicketCreate, TicketStatusUpdate, TicketUpdate
from app.services.ticket import TicketService

router = APIRouter(prefix="/api/desk/tickets", tags=["desk-tickets"])


@router.get("")
async def list_tickets(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    priority_filter: str | None = Query(default=None, alias="priority"),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TicketService.list_tickets(
        session, limit=limit, offset=offset,
        status_filter=status_filter, priority_filter=priority_filter, keyword=keyword,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TicketService.create_ticket(session, payload, request)


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TicketService.get_ticket(session, ticket_id)


@router.patch("/{ticket_id}")
async def update_ticket(
    ticket_id: str, payload: TicketUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TicketService.update_ticket(session, ticket_id, payload, request)


@router.patch("/{ticket_id}/status")
async def change_status(
    ticket_id: str, payload: TicketStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TicketService.change_status(session, ticket_id, payload.status, request)


@router.get("/{ticket_id}/sla")
async def ticket_sla(
    ticket_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TicketService.sla_status(session, ticket_id)
