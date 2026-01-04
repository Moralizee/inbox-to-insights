from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from db import Base
from db import engine

Base.metadata.create_all(bind=engine)

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
    risk_flags = Column(Text)   # stored as comma-separated values

    preview = Column(Text)
    body = Column(Text)

    links = relationship("EmailLink", back_populates="email", cascade="all, delete")


class EmailLink(Base):
    __tablename__ = "email_links"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"))

    url = Column(Text)
    domain = Column(String)

    email = relationship("Email", back_populates="links")
