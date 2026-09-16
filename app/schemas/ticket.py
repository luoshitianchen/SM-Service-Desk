"""工单 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    requester: str = Field(min_length=1, max_length=128)
    assignee: str = Field(default="", max_length=128)
    service_catalog_item_id: str | None = Field(default=None, max_length=64)
    sla_id: str | None = Field(default=None, max_length=64)


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    priority: Literal["low", "medium", "high", "urgent"] | None = None
    assignee: str | None = Field(default=None, max_length=128)
    resolution: str | None = Field(default=None, max_length=4000)


class TicketStatusUpdate(BaseModel):
    status: Literal["open", "assigned", "in_progress", "resolved", "closed"]


class TicketResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    priority: str
    requester: str
    assignee: str
    service_catalog_item_id: str
    sla_id: str
    resolution: str
    due_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    total: int
    items: list[TicketResponse]
