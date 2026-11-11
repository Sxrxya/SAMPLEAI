from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, applications, auth, jobs, profiles, resumes
from app.core.config import get_settings
from app.core.db import Base, engine
from app.services.search import initialize_search_index


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.validate_auth_secret()
    settings.validate_inference()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)
    initialize_search_index()
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))[:100]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "detail": exc.detail,
            "code": f"http_{exc.status_code}",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.get("/")
def root() -> dict:
    return {
        "message": "Tandem AI Recruitment Platform Backend API",
        "status": "online",
        "docs_url": "/docs",
        "health": "/health",
        "api_v1": "/api/v1",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


for route in (
    auth.router,
    profiles.router,
    resumes.router,
    jobs.router,
    applications.router,
    admin.router,
):
    app.include_router(route, prefix=settings.api_v1_prefix)
