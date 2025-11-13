import datetime as dt
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.services import risk


async def create_session(
    db: AsyncSession,
    *,
    user_id: str,
    family_id: str,
    jti: str,
    idx: int,
    refresh_ttl_days: int,
    user_agent: str | None,
    ip: str | None,
) -> Session:
    expires_at = dt.datetime.utcnow() + dt.timedelta(days=refresh_ttl_days)
    ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else None
    session = Session(
        user_id=user_id,
        jti=jti,
        family_id=family_id,
        idx=idx,
        user_agent=user_agent,
        ip_hash=ip_hash,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()
    return session


async def get_session_by_jti(db: AsyncSession, jti: str) -> Session | None:
    result = await db.execute(select(Session).where(Session.jti == jti))
    return result.scalar_one_or_none()


async def rotate_session(
    db: AsyncSession,
    *,
    session: Session,
    new_jti: str,
    new_idx: int,
    refresh_ttl_days: int,
) -> None:
    session.jti = new_jti
    session.idx = new_idx
    session.last_rotated_at = dt.datetime.utcnow()
    session.expires_at = dt.datetime.utcnow() + dt.timedelta(days=refresh_ttl_days)
    await db.flush()


async def mark_revoked(db: AsyncSession, session: Session) -> None:
    session.revoked_at = dt.datetime.utcnow()
    await db.flush()


async def revoke_family(redis_conn, family_id: str, refresh_ttl_days: int) -> None:
    await risk.revoke_family(redis_conn, family_id, refresh_ttl_days * 24 * 3600)
