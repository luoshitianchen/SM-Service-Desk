"""服务目录管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.service_catalog import CatalogItemCreate, CatalogItemUpdate
from app.services.service_catalog import CatalogService

router = APIRouter(prefix="/api/desk/catalog-items", tags=["desk-catalog"])


@router.get("")
async def list_items(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    keyword: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CatalogService.list_items(
        session, limit=limit, offset=offset, category=category,
        is_active=is_active, keyword=keyword,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: CatalogItemCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CatalogService.create_item(session, payload, request)


@router.get("/{item_id}")
async def get_item(
    item_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CatalogService.get_item(session, item_id)


@router.patch("/{item_id}")
async def update_item(
    item_id: str, payload: CatalogItemUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CatalogService.update_item(session, item_id, payload, request)


@router.delete("/{item_id}")
async def delete_item(
    item_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await CatalogService.delete_item(session, item_id, request)
