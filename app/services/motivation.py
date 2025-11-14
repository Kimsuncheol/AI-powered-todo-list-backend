from datetime import datetime, timezone
from typing import Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.quotes import get_quote_for_current_hour

model = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
parser = StrOutputParser()

prompt = ChatPromptTemplate.from_template(
    "You are a friendly motivational assistant for a productivity app.\n"
    "User name: {user_name}\n"
    "Use the given quote as the anchor and craft a short motivational message.\n"
    'Quote: "{quote_text}" by {quote_author}\n'
    "Constraints:\n"
    "- Under 30 words\n"
    "- Concise and positive\n"
    "- Address the user naturally (use their name if helpful)\n"
    "- Assume this message is for the current hour of the day.\n"
)


async def generate_hourly_motivation(
    db: AsyncSession,
    user_name: str,
    locale: Optional[str] = None,
    now: Optional[datetime] = None,
) -> str:
    if now is None:
        now = datetime.now(timezone.utc)

    quote = await get_quote_for_current_hour(db, now=now, locale=locale)

    if not quote:
        return "Keep going. Small steps this hour become big wins tomorrow."

    chain = prompt | model | parser
    return await chain.ainvoke(
        {
            "user_name": user_name,
            "quote_text": quote.text,
            "quote_author": quote.author or "Unknown",
        }
    )
