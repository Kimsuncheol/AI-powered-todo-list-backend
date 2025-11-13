import hashlib

import redis.asyncio as redis

from app.core.config import settings

LOCK_PREFIX = "auth:lock:"
IP_COUNTER_PREFIX = "auth:ip:"
EMAIL_COUNTER_PREFIX = "auth:email:"
FAMILY_REVOKE_PREFIX = "auth:revoke:"
FAIL_COUNTER_PREFIX = "auth:fail:"


def _hash_ip(ip: str | None) -> str:
    if not ip:
        return "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()


def _email_key(email: str) -> str:
    return email.strip().lower()


def _lock_key(email: str) -> str:
    return f"{LOCK_PREFIX}{_email_key(email)}"


def _ip_key(ip: str) -> str:
    return f"{IP_COUNTER_PREFIX}{ip}"


def _email_counter_key(email: str) -> str:
    return f"{EMAIL_COUNTER_PREFIX}{_email_key(email)}"


def _fail_key(email: str) -> str:
    return f"{FAIL_COUNTER_PREFIX}{_email_key(email)}"


def family_revoke_key(family_id: str) -> str:
    return f"{FAMILY_REVOKE_PREFIX}{family_id}"


async def hit_signin(redis_conn: redis.Redis, email: str, ip: str | None) -> tuple[int, int]:
    hashed_ip = _hash_ip(ip)
    ip_key = _ip_key(hashed_ip)
    ip_count = await redis_conn.incr(ip_key)
    await redis_conn.expire(ip_key, settings.rate_limit.signin_ip_window_s)

    email_key = _email_counter_key(email)
    email_count = await redis_conn.incr(email_key)
    await redis_conn.expire(
        email_key, settings.rate_limit.signin_email_window_s
    )
    return ip_count, email_count


async def after_fail(redis_conn: redis.Redis, email: str) -> bool:
    fails = await redis_conn.incr(_fail_key(email))
    await redis_conn.expire(
        _fail_key(email), settings.rate_limit.signin_email_window_s
    )
    if fails >= settings.rate_limit.signin_email_max:
        await lock(redis_conn, email, settings.rate_limit.lock_minutes * 60)
        return True
    return False


async def reset_fail(redis_conn: redis.Redis, email: str) -> None:
    await redis_conn.delete(_fail_key(email))


async def is_locked(redis_conn: redis.Redis, email: str) -> bool:
    ttl = await redis_conn.ttl(_lock_key(email))
    if ttl is None:
        return False
    if ttl == -2:
        return False
    return ttl == -1 or ttl > 0


async def lock(redis_conn: redis.Redis, email: str, ttl_s: int) -> None:
    await redis_conn.set(_lock_key(email), 1, ex=ttl_s)


async def captcha_hint(redis_conn: redis.Redis, email: str) -> bool:
    count = await redis_conn.get(_fail_key(email))
    if not count:
        return False
    return int(count) >= settings.rate_limit.captcha_hint_after


def is_rate_limited(ip_count: int, email_count: int) -> bool:
    return (
        ip_count > settings.rate_limit.signin_ip_max
        or email_count > settings.rate_limit.signin_email_max
    )


async def revoke_family(redis_conn: redis.Redis, family_id: str, ttl_seconds: int) -> None:
    await redis_conn.set(family_revoke_key(family_id), 1, ex=ttl_seconds)


async def is_family_revoked(redis_conn: redis.Redis, family_id: str) -> bool:
    return bool(await redis_conn.exists(family_revoke_key(family_id)))
