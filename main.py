from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth as auth_routes
from app.core.config import settings
from app.core.db import Base, engine
from app.utils.middleware import CSRFMiddleware, EnforceHTTPSMiddleware

EXEMPT_CSRF_PATHS = {
    "/auth/signin",
    "/auth/signup",
    "/auth/otp/start",
    "/auth/otp/verify",
    "/auth/password/reset",
}


def create_app() -> FastAPI:
    app = FastAPI(title=settings.api_title, version=settings.api_version)

    app.add_middleware(EnforceHTTPSMiddleware)
    app.add_middleware(
        CSRFMiddleware,
        exempt_paths=EXEMPT_CSRF_PATHS,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"https://{settings.cookie_domain}",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(auth_routes.router)

    @app.on_event("startup")
    async def on_startup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @app.get("/", tags=["misc"])
    async def root():
        return {"message": "AI Todo Auth API"}

    @app.get("/health", tags=["misc"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
