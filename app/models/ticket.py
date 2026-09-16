"""工单模型：IT 服务台核心实体。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class Ticket(Base):
    """工单：覆盖从提单到关闭的全生命周期。"""

    __tablename__ = "desk_tickets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # 状态机：open -> assigned -> in_progress -> resolved -> closed
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    # 优先级：low / medium / high / urgent
    priority: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    requester: Mapped[str] = mapped_column(String(128), default="", index=True)
    assignee: Mapped[str] = mapped_column(String(128), default="")
    service_catalog_item_id: Mapped[str] = mapped_column(String(64), default="")
    sla_id: Mapped[str] = mapped_column(String(64), default="")
    resolution: Mapped[str] = mapped_column(Text, default="")
    # SLA 承诺解决时限，创建时依据 SLA 策略计算
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
