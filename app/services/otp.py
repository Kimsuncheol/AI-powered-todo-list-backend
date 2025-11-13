import hashlib
import secrets
import string
import uuid
from datetime import timedelta

import redis.asyncio as redis

from app.services import email as email_service

OTP_KEY_PREFIX = "otp:email:"
OTP_TICKET_PREFIX = "otp:ticket:"
OTP_TTL_SECONDS = 600
TICKET_TTL_SECONDS = 600
MAX_ATTEMPTS = 5


def _otp_key(email: str) -> str:
    return f"{OTP_KEY_PREFIX}{email.lower()}"


def _ticket_key(ticket: str) -> str:
    return f"{OTP_TICKET_PREFIX}{ticket}"


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def _generate_otp() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


async def start(redis_conn: redis.Redis, email: str) -> str:
    otp = _generate_otp()
    key = _otp_key(email)
    digest = hashlib.sha256(otp.encode()).hexdigest()
    await redis_conn.hset(key, mapping={"otp_hash": digest, "attempts": 0})
    await redis_conn.expire(key, OTP_TTL_SECONDS)
    await email_service.send_mail(
        subject="Your password reset code",
        recipients=[email],
        body=f"<p>Your OTP code is <strong>{otp}</strong>. It expires in 10 minutes.</p>",
    )
    return _mask_email(email)


async def verify(redis_conn: redis.Redis, email: str, otp: str) -> str | None:
    key = _otp_key(email)
    stored = await redis_conn.hgetall(key)
    if not stored:
        return None
    attempts = int(stored.get("attempts", 0)) + 1
    if attempts > MAX_ATTEMPTS:
        await redis_conn.delete(key)
        return None
    await redis_conn.hset(key, "attempts", attempts)
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    if not stored.get("otp_hash") or not secrets.compare_digest(stored.get("otp_hash"), otp_hash):
        return None
    ticket = str(uuid.uuid4())
    await redis_conn.set(_ticket_key(ticket), email.lower(), ex=TICKET_TTL_SECONDS)
    await redis_conn.delete(key)
    return ticket


async def consume(redis_conn: redis.Redis, ticket: str) -> str | None:
    key = _ticket_key(ticket)
    email = await redis_conn.get(key)
    if not email:
        return None
    await redis_conn.delete(key)
    return email
