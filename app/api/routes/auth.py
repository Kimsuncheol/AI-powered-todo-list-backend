import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.redis import get_redis
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import (
    AuthEnvelope,
    OtpStartIn,
    OtpVerifyIn,
    PasswordResetIn,
    SignInIn,
    SignUpIn,
    UserPublic,
)
from app.services import audit, otp, password as password_service, risk, session as session_service
from app.services.tokens import decode_refresh, issue_access, issue_refresh

router = APIRouter(prefix="/auth", tags=["auth"])

GENERIC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
)


def _set_auth_cookies(resp: Response, access: str, refresh: str) -> None:
    resp.set_cookie(
        "access_token",
        access,
        httponly=True,
        secure=True,
        samesite="lax",
        domain=settings.cookie_domain,
        max_age=settings.access_token_minutes * 60,
    )
    resp.set_cookie(
        "refresh_token",
        refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        domain=settings.cookie_domain,
        max_age=settings.refresh_token_days * 24 * 3600,
    )
    csrf_token = str(uuid.uuid4())
    resp.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        httponly=False,
        secure=True,
        samesite="lax",
        domain=settings.cookie_domain,
        max_age=settings.refresh_token_days * 24 * 3600,
    )
    resp.headers[settings.csrf_header_name] = csrf_token


def _clear_auth_cookies(resp: Response) -> None:
    resp.delete_cookie("access_token", domain=settings.cookie_domain)
    resp.delete_cookie("refresh_token", domain=settings.cookie_domain)
    resp.delete_cookie(settings.csrf_cookie_name, domain=settings.cookie_domain)


def _public_user(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        name=user.name,
        tz=user.tz,
        locale=user.locale,
        emailVerified=user.email_verified,
    )


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post("/signup", response_model=AuthEnvelope)
async def signup(
    req: SignUpIn,
    request: Request,
    resp: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    # request: Request | None = None,
):
    if await risk.is_locked(redis, req.email):
        raise GENERIC
    user = User(email=req.email, password_hash=password_service.hash_password(req.password), name=req.name)
    try:
        async with db.begin():
            db.add(user)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to complete request")

    family_id = str(uuid.uuid4())
    refresh, jti, idx, _ = issue_refresh(user.id, family_id, 0)
    async with db.begin():
        await session_service.create_session(
            db,
            user_id=user.id,
            family_id=family_id,
            jti=jti,
            idx=idx,
            refresh_ttl_days=settings.refresh_token_days,
            user_agent=request.headers.get("user-agent"),
            ip=_client_ip(request),
            # user_agent=request.headers.get("user-agent") if request else None,
            # ip=_client_ip(request) if request else None,
        )
        await audit.record_event(
            db,
            user_id=user.id,
            event="signup",
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            # ip=_client_ip(request) if request else None,
            # user_agent=request.headers.get("user-agent") if request else None,
        )

    access = issue_access(user.id, jti)
    _set_auth_cookies(resp, access, refresh)

    return AuthEnvelope(data=_public_user(user))


@router.post("/signin", response_model=AuthEnvelope)
async def signin(
    req: SignInIn,
    request: Request,
    resp: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    ip = _client_ip(request)
    if await risk.is_locked(redis, req.email):
        raise GENERIC

    ip_count, email_count = await risk.hit_signin(redis, req.email, ip)
    if risk.is_rate_limited(ip_count, email_count):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Slow down")

    user: User | None
    async with db.begin():
        result = await db.execute(select(User).where(User.email == req.email))
        user = result.scalar_one_or_none()
    if not user or not password_service.verify_password(user.password_hash, req.password):
        await risk.after_fail(redis, req.email)
        headers: dict[str, str] | None = None
        if await risk.captcha_hint(redis, req.email):
            headers = {"X-Captcha-Hint": "true"}
        async with db.begin():
            await audit.record_event(
                db,
                user_id=user.id if user else None,
                event="signin.fail",
                ip=ip,
                user_agent=request.headers.get("user-agent"),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers=headers
        )

    await risk.reset_fail(redis, req.email)

    family_id = str(uuid.uuid4())
    refresh, jti, idx, _ = issue_refresh(user.id, family_id, 0)
    async with db.begin():
        await session_service.create_session(
            db,
            user_id=user.id,
            family_id=family_id,
            jti=jti,
            idx=idx,
            refresh_ttl_days=settings.refresh_token_days,
            user_agent=request.headers.get("user-agent"),
            ip=ip,
        )
        await audit.record_event(
            db,
            user_id=user.id,
            event="signin.success",
            ip=ip,
            user_agent=request.headers.get("user-agent"),
        )

    access = issue_access(user.id, jti)
    _set_auth_cookies(resp, access, refresh)

    return AuthEnvelope(data=_public_user(user))


@router.post("/signout", status_code=204)
async def signout(
    resp: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            payload = decode_refresh(refresh_token)
        except Exception:
            payload = None
        if payload:
            session: Session | None
            async with db.begin():
                session = await session_service.get_session_by_jti(db, payload["jti"])
                if session:
                    await session_service.mark_revoked(db, session)
            if session:
                await session_service.revoke_family(redis, session.family_id, settings.refresh_token_days)
    _clear_auth_cookies(resp)
    resp.status_code = 204
    return resp


@router.post("/refresh", response_model=AuthEnvelope)
async def refresh(
    request: Request,
    resp: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise GENERIC
    try:
        payload = decode_refresh(refresh_token)
    except Exception:
        raise GENERIC

    session: Session | None
    async with db.begin():
        session = await session_service.get_session_by_jti(db, payload["jti"])
    if not session or session.family_id != payload.get("fam"):
        if session:
            async with db.begin():
                await session_service.mark_revoked(db, session)
        await session_service.revoke_family(redis, payload.get("fam", str(uuid.uuid4())), settings.refresh_token_days)
        raise GENERIC

    if session.revoked_at or await risk.is_family_revoked(redis, session.family_id):
        raise GENERIC

    if session.idx != payload.get("idx"):
        await session_service.revoke_family(redis, session.family_id, settings.refresh_token_days)
        if not session.revoked_at:
            async with db.begin():
                await session_service.mark_revoked(db, session)
        raise GENERIC

    user: User
    new_jti: str
    new_refresh: str
    async with db.begin():
        user = await db.get(User, session.user_id)
        if not user:
            raise GENERIC
        new_idx = session.idx + 1
        new_refresh, new_jti, _, _ = issue_refresh(user.id, session.family_id, new_idx)
        await session_service.rotate_session(
            db,
            session=session,
            new_jti=new_jti,
            new_idx=new_idx,
            refresh_ttl_days=settings.refresh_token_days,
        )
        await audit.record_event(
            db,
            user_id=user.id,
            event="refresh",
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

    access = issue_access(user.id, new_jti)
    _set_auth_cookies(resp, access, new_refresh)
    return AuthEnvelope(data=_public_user(user))


@router.post("/otp/start", status_code=204)
async def otp_start(req: OtpStartIn, redis=Depends(get_redis)):
    try:
        await otp.start(redis, req.email)
    except Exception:
        pass
    return Response(status_code=204)


@router.post("/otp/verify", status_code=204)
async def otp_verify(req: OtpVerifyIn, resp: Response, redis=Depends(get_redis)):
    try:
        ticket = await otp.verify(redis, req.email, req.otp)
        if ticket:
            resp.set_cookie(
                "otp_ticket",
                ticket,
                httponly=True,
                secure=True,
                samesite="lax",
                domain=settings.cookie_domain,
                max_age=10 * 60,
            )
    except Exception:
        pass
    resp.status_code = 204
    return resp


@router.post("/password/reset", status_code=204)
async def password_reset(
    req: PasswordResetIn,
    request: Request,
    resp: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    ticket = request.cookies.get("otp_ticket")
    resp.status_code = 204
    if not ticket:
        return resp
    email_from_ticket = await otp.consume(redis, ticket)
    resp.delete_cookie("otp_ticket", domain=settings.cookie_domain)
    if not email_from_ticket or email_from_ticket != req.email.lower():
        return resp

    user: User | None
    async with db.begin():
        result = await db.execute(select(User).where(User.email == req.email))
        user = result.scalar_one_or_none()
    if not user:
        return resp

    async with db.begin():
        user.password_hash = password_service.hash_password(req.new_password)
        await audit.record_event(
            db,
            user_id=user.id,
            event="reset.finish",
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        await db.flush()
    sessions: list[Session]
    async with db.begin():
        sessions = (await db.execute(select(Session).where(Session.user_id == user.id))).scalars().all()
    async with db.begin():
        for sess in sessions:
            await session_service.mark_revoked(db, sess)
            await session_service.revoke_family(redis, sess.family_id, settings.refresh_token_days)

    return resp
