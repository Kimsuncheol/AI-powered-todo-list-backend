from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.motivation import MotivationOut, QuoteOut
from app.services.motivation import generate_hourly_motivation
from app.services.quotes import get_quote_for_current_hour

router = APIRouter(prefix="/motivation", tags=["motivation"])


@router.get("/now", response_model=MotivationOut)
async def get_current_motivation(
    name: str = "Friend",
    locale: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> MotivationOut:
    now = datetime.now(timezone.utc)
    message = await generate_hourly_motivation(db, user_name=name, locale=locale, now=now)
    quote = await get_quote_for_current_hour(db, now=now, locale=locale)

    return MotivationOut(
        message=message,
        quote=QuoteOut(
            text=quote.text,
            author=quote.author,
            locale=quote.locale,
        )
        if quote
        else None,
    )
