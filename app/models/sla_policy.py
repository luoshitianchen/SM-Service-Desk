"""SLA 策略模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class SLAPolicy(Base):
    """SLA 策略：按优先级定义响应与解决时限（分钟）。"""

    __tablename__ = "desk_slas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # 适用优先级：low / medium / high / urgent
    priority: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    response_minutes: Mapped[int] = mapped_column(Integer, default=30)
    resolution_minutes: Mapped[int] = mapped_column(Integer, default=240)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
