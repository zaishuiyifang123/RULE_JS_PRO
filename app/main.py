from fastapi import FastAPI

from app.routers import auth, admin


def create_app() -> FastAPI:
    app = FastAPI(title="Edu Cockpit API", version="1.0.0")

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

    return app


app = create_app()
