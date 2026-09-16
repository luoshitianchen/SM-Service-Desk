"""SLA 策略 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SLACreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    response_minutes: int = Field(default=30, ge=1, le=10080)
    resolution_minutes: int = Field(default=240, ge=1, le=10080)


class SLAUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    response_minutes: int | None = Field(default=None, ge=1, le=10080)
    resolution_minutes: int | None = Field(default=None, ge=1, le=10080)
    is_active: bool | None = None


class SLAResponse(BaseModel):
    id: str
    name: str
    priority: str
    response_minutes: int
    resolution_minutes: int
    is_active: bool
    created_at: datetime


class SLAListResponse(BaseModel):
    total: int
    items: list[SLAResponse]
