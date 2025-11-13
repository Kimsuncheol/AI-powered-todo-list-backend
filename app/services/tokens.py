import datetime as dt
import uuid
from typing import Tuple

import jwt

from app.core.config import settings

ACCESS_MIN = settings.access_token_minutes
REFRESH_DAYS = settings.refresh_token_days


def issue_access(user_id: str, session_jti: str) -> str:
    now = dt.datetime.utcnow()
    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "sid": session_jti,
        "iat": now,
        "exp": now + dt.timedelta(minutes=ACCESS_MIN),
        "iss": settings.jwt_iss,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def issue_refresh(user_id: str, family_id: str, idx: int) -> Tuple[str, str, int, str]:
    now = dt.datetime.utcnow()
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "jti": jti,
        "fam": family_id,
        "idx": idx,
        "iat": now,
        "exp": now + dt.timedelta(days=REFRESH_DAYS),
        "iss": settings.jwt_iss,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256"), jti, idx, family_id


def decode_refresh(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], issuer=settings.jwt_iss)
