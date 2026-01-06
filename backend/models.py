from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    ForeignKey, Text, DateTime
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import expression
from datetime import datetime

from db import Base, engine

from typing import Optional


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    subject: Mapped[str] = mapped_column(String)
    from_raw: Mapped[str] = mapped_column(String)
    from_name: Mapped[str] = mapped_column(String)
    from_email: Mapped[str] = mapped_column(String)

    sender_domain: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String)

    is_noreply: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=expression.false()
    )

    category: Mapped[str] = mapped_column(String)
    intent: Mapped[str] = mapped_column(String)

    risk_score: Mapped[float] = mapped_column(Float)
    risk_flags: Mapped[str] = mapped_column(Text)

    preview: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)

    # ======== AI Intelligence Fields (NEW) ========

    summary: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True, 
        comment="AI-generated summary of the email content"
    )

    ai_tasks: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True, 
        comment="Semicolon-separated list of extracted action items"
    )

    # ======== Reply / Action Intelligence ========

    requires_reply: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=expression.false()
    )

    action_request: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=expression.false()
    )

    urgency: Mapped[str] = mapped_column(
        String,
        default="none",
        server_default="none"
    )

    reply_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0"
    )

    reply_flags: Mapped[str] = mapped_column(Text)

    # ======== Assignment Workflow ========

    status: Mapped[str] = mapped_column(
        String,
        default="open",
        server_default="open"
    )

    assignee_name: Mapped[Optional[str]] = mapped_column(
        String, 
        nullable=True, 
        default=None
    )
    assignee_email: Mapped[Optional[str]] = mapped_column(
        String, 
        nullable=True, 
        default=None
    )

    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None
    )

    links = relationship(
        "EmailLink",
        back_populates="email",
        cascade="all, delete"
    )


class EmailLink(Base):
    __tablename__ = "email_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"))

    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String)

    email = relationship("Email", back_populates="links")


# This ensures tables are created when this script is run
Base.metadata.create_all(bind=engine)