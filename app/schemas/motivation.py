from pydantic import BaseModel


class QuoteOut(BaseModel):
    text: str
    author: str | None = None
    locale: str | None = None


class MotivationOut(BaseModel):
    message: str
    quote: QuoteOut | None = None
