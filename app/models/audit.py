from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.mysql import CHAR

from app.core.db import Base
import uuid


def uuid_str() -> str:
    return str(uuid.uuid4())


class AuthAudit(Base):
    __tablename__ = "auth_audit"

    id = Column(CHAR(36), primary_key=True, default=uuid_str)
    user_id = Column(CHAR(36))
    event = Column(String(64), nullable=False)
    ip = Column(String(64))
    ua = Column(String(512))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
