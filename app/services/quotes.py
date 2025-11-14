from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote


async def get_quote_for_current_hour(
    db: AsyncSession,
    now: Optional[datetime] = None,
    locale: Optional[str] = None,
) -> Optional[Quote]:
    """Return the deterministic quote for the current UTC hour."""
    if now is None:
        now = datetime.now(timezone.utc)

    base_stmt = select(Quote)
    if locale:
        base_stmt = base_stmt.where(Quote.locale == locale)

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    result = await db.execute(count_stmt)
    count = result.scalar_one()

    if count == 0:
        return None

    hour_index = int(now.timestamp() // 3600)
    offset = hour_index % count

    stmt = base_stmt.order_by(Quote.id).offset(offset).limit(1)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()
