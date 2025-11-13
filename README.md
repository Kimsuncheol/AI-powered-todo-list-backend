# AI Todo Auth Backend

FastAPI backend that exposes secure authentication endpoints backed by MySQL 8 (async SQLAlchemy) and Redis.

## Quickstart

1. Copy `.env.example` to `.env` and fill in secrets (MySQL, Redis, mail, JWT, cookie domain).
2. Install dependencies: `pip install -r requirements.txt`.
3. Run migrations: `alembic revision --autogenerate -m "init" && alembic upgrade head`.
4. Start the API: `uvicorn main:app --reload`.

## Environment Variables

| Key | Description |
| --- | --- |
| `DATABASE_URL` | `mysql+asyncmy://user:pass@host:3306/db?charset=utf8mb4` |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET` | HS256 secret |
| `JWT_ISS` | JWT issuer URL |
| `COOKIE_DOMAIN` | Primary domain for cookies |
| `MAIL_HOST`/`MAIL_PORT`/`MAIL_USERNAME`/`MAIL_PASSWORD`/`MAIL_SENDER` | SMTP creds for OTP mail |
| `MAIL_USE_TLS` | `true`/`false` |

Optional knobs are in `app/core/config.py` (rate limits, HTTPS enforcement, etc.).

## Testing Notes

* Access tokens live for 15 minutes; refresh for 7 days and rotate on every `/auth/refresh` call.
* Refresh cookies are httpOnly+Secure; CSRF double-submit header is required for mutating routes once cookies are set.
* Redis is required for rate limiting, lockouts, OTP, and refresh family revocation.
