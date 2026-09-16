"""服务目录项 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CatalogItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="", max_length=64)
    sla_id: str | None = Field(default=None, max_length=64)


class CatalogItemUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=64)
    sla_id: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None


class CatalogItemResponse(BaseModel):
    id: str
    name: str
    code: str
    description: str
    category: str
    sla_id: str
    is_active: bool
    created_at: datetime


class CatalogItemListResponse(BaseModel):
    total: int
    items: list[CatalogItemResponse]
