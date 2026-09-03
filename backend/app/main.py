"""
FastAPI application entrypoint: app wiring, CORS, MongoDB lifecycle, and
route registration.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, interviews, resumes
from app.core.config import settings
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.interview.repository import ensure_indexes as ensure_interview_indexes
from app.resume.repository import ensure_indexes as ensure_resume_indexes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    db = get_database()
    await ensure_interview_indexes(db)
    await ensure_resume_indexes(db)
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(interviews.router, prefix="/api", tags=["interviews"])
app.include_router(resumes.router, prefix="/api", tags=["resumes"])


@app.get("/")
async def root() -> dict:
    return {"message": settings.app_name, "docs": "/docs"}
