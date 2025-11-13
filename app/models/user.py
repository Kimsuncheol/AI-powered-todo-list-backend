from sqlalchemy import Boolean, Column, DateTime, String, func
from sqlalchemy.dialects.mysql import CHAR

from app.core.db import Base
import uuid


def uuid_str() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=uuid_str)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(120), nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    tz = Column(String(64), default="Asia/Seoul", nullable=False)
    locale = Column(String(16), default="ko-KR", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
