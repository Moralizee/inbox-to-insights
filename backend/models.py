from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from db import Base
from db import engine

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)

    subject = Column(String)
    from_raw = Column(String)
    from_name = Column(String)
    from_email = Column(String)

    sender_domain = Column(String)
    provider = Column(String)
    is_noreply = Column(Boolean, default=False)

    category = Column(String)
    intent = Column(String)

    risk_score = Column(Float)
    risk_flags = Column(Text)   # "; " separated

    preview = Column(Text)
    body = Column(Text)

    # ======== NEW Reply / Action Intelligence Fields ========

    requires_reply = Column(Boolean, default=False)
    action_request = Column(Boolean, default=False)

    # whether the message is assigned to user
    assigned_to_user = Column(Boolean, default=False)

    # "none" | "medium" | "high"
    urgency = Column(String, default="none")

    # 0.0 — 1.0 confidence score
    reply_score = Column(Float, default=0.0)

    # "; " separated explanation flags
    reply_flags = Column(Text)

    # ========================================================

    links = relationship(
        "EmailLink",
        back_populates="email",
        cascade="all, delete"
    )


class EmailLink(Base):
    __tablename__ = "email_links"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"))

    url = Column(Text)
    domain = Column(String)

    email = relationship("Email", back_populates="links")


Base.metadata.create_all(bind=engine)
