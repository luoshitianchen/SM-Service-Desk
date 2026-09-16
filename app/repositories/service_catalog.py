"""服务目录项仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_catalog import ServiceCatalogItem


async def get_item(session: AsyncSession, item_id: str) -> ServiceCatalogItem | None:
    result = await session.execute(select(ServiceCatalogItem).where(ServiceCatalogItem.id == item_id))
    return result.scalar_one_or_none()


async def get_item_by_code(session: AsyncSession, code: str) -> ServiceCatalogItem | None:
    result = await session.execute(select(ServiceCatalogItem).where(ServiceCatalogItem.code == code))
    return result.scalar_one_or_none()


async def list_items(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    category: str | None = None,
    is_active: bool | None = None,
    keyword: str | None = None,
) -> list[ServiceCatalogItem]:
    stmt = select(ServiceCatalogItem).order_by(ServiceCatalogItem.created_at.desc()).limit(limit).offset(offset)
    if category:
        stmt = stmt.where(ServiceCatalogItem.category == category)
    if is_active is not None:
        stmt = stmt.where(ServiceCatalogItem.is_active == is_active)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(ServiceCatalogItem.name.like(like), ServiceCatalogItem.code.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_items(
    session: AsyncSession,
    category: str | None = None,
    is_active: bool | None = None,
    keyword: str | None = None,
) -> int:
    stmt = select(func.count(ServiceCatalogItem.id))
    if category:
        stmt = stmt.where(ServiceCatalogItem.category == category)
    if is_active is not None:
        stmt = stmt.where(ServiceCatalogItem.is_active == is_active)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(ServiceCatalogItem.name.like(like), ServiceCatalogItem.code.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_item(session: AsyncSession, item: ServiceCatalogItem) -> ServiceCatalogItem:
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def update_item(session: AsyncSession, item: ServiceCatalogItem) -> ServiceCatalogItem:
    await session.commit()
    await session.refresh(item)
    return item


async def delete_item(session: AsyncSession, item: ServiceCatalogItem) -> None:
    await session.delete(item)
    await session.commit()
