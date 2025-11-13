from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuthAudit


async def record_event(
    db: AsyncSession,
    *,
    user_id: str | None,
    event: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    audit = AuthAudit(user_id=user_id, event=event, ip=ip, ua=user_agent)
    db.add(audit)
    await db.flush()
