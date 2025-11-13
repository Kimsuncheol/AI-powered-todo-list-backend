from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.dialects.mysql import CHAR

from app.core.db import Base
import uuid


def uuid_str() -> str:
    return str(uuid.uuid4())


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(CHAR(36), primary_key=True, default=uuid_str)
    email_lower = Column(String(255), index=True, nullable=False)
    otp_hash = Column(String(255), nullable=False)
    otp_expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    consumed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
