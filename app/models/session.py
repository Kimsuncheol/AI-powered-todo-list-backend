from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.mysql import CHAR

from app.core.db import Base
import uuid


def uuid_str() -> str:
    return str(uuid.uuid4())


class Session(Base):
    __tablename__ = "sessions"

    id = Column(CHAR(36), primary_key=True, default=uuid_str)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    jti = Column(CHAR(36), unique=True, nullable=False)
    family_id = Column(CHAR(36), nullable=False)
    user_agent = Column(String(512))
    ip_hash = Column(String(128))
    idx = Column(Integer, default=0, nullable=False)
    last_rotated_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
