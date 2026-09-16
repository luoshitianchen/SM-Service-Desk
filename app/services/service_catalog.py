"""服务目录服务层。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.service_catalog import ServiceCatalogItem
from app.repositories import service_catalog as repo
from app.schemas.service_catalog import CatalogItemCreate, CatalogItemUpdate
from app.services.audit import record_audit


def _item_to_dict(i: ServiceCatalogItem) -> dict:
    return {
        "id": i.id, "name": i.name, "code": i.code, "description": i.description,
        "category": i.category, "sla_id": i.sla_id, "is_active": i.is_active,
        "created_at": i.created_at.isoformat() if i.created_at else "",
    }


class CatalogService:
    @staticmethod
    async def list_items(
        session: AsyncSession, limit: int = 100, offset: int = 0,
        category: str | None = None, is_active: bool | None = None, keyword: str | None = None,
    ) -> dict:
        items = await repo.list_items(
            session, limit=limit, offset=offset, category=category,
            is_active=is_active, keyword=keyword,
        )
        total = await repo.count_items(session, category=category, is_active=is_active, keyword=keyword)
        return {"total": total, "items": [_item_to_dict(i) for i in items]}

    @staticmethod
    async def get_item(session: AsyncSession, item_id: str) -> dict:
        item = await repo.get_item(session, item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "目录项不存在")
        return _item_to_dict(item)

    @staticmethod
    async def create_item(session: AsyncSession, payload: CatalogItemCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if await repo.get_item_by_code(session, payload.code):
            raise HTTPException(status.HTTP_409_CONFLICT, "服务编码已存在")
        item = ServiceCatalogItem(
            id=str(uuid.uuid4()), name=payload.name, code=payload.code,
            description=payload.description, category=payload.category,
            sla_id=payload.sla_id or "", is_active=True,
        )
        item = await repo.create_item(session, item)
        await record_audit(session, "catalog.created", "internal",
                           f"code={payload.code}", request)
        return _item_to_dict(item)

    @staticmethod
    async def update_item(session: AsyncSession, item_id: str, payload: CatalogItemUpdate,
                          request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        item = await repo.get_item(session, item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "目录项不存在")
        if payload.name is not None:
            item.name = payload.name
        if payload.description is not None:
            item.description = payload.description
        if payload.category is not None:
            item.category = payload.category
        if payload.sla_id is not None:
            item.sla_id = payload.sla_id
        if payload.is_active is not None:
            item.is_active = payload.is_active
        item = await repo.update_item(session, item)
        await record_audit(session, "catalog.updated", "internal", f"item_id={item_id}", request)
        return _item_to_dict(item)

    @staticmethod
    async def delete_item(session: AsyncSession, item_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        item = await repo.get_item(session, item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "目录项不存在")
        code = item.code
        await repo.delete_item(session, item)
        await record_audit(session, "catalog.deleted", "internal",
                           f"item_id={item_id} code={code}", request)
        return {"deleted": True, "id": item_id}
