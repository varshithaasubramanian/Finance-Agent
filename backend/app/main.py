"""
AI Personal Finance & Budget Agent -- FastAPI application entrypoint.

Run with:  uvicorn app.main:app --reload
Docs at:   http://localhost:8000/docs
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import ai, analytics, auth, budgets, categories, expenses, goals, recurring
from app.config import get_settings
from app.database.db import init_db, session_scope
from app.database.seed import seed_demo_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finance_agent")

settings = get_settings()

app = FastAPI(
    title="AI Personal Finance & Budget Agent API",
    description=(
        "Backend API for a personal budgeting and expense-tracking application with "
        "an AI financial assistant. All financial calculations are deterministic and "
        "server-side; the AI layer only narrates results retrieved from this API and "
        "has a full rule-based fallback when no AI provider is configured. Every "
        "resource is scoped to the authenticated user via JWT (see /api/auth)."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred.", "error_code": "internal_error"})


app.include_router(auth.router)
app.include_router(budgets.router)
app.include_router(categories.router)
app.include_router(expenses.router)
app.include_router(analytics.router)
app.include_router(ai.router)
app.include_router(goals.router)
app.include_router(recurring.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    if settings.seed_demo_data:
        with session_scope() as db:
            seed_demo_data(db)
    logger.info("AI Personal Finance & Budget Agent API started. AI enabled: %s", settings.ai_enabled)


@app.get("/", tags=["health"])
def root():
    return {
        "name": "AI Personal Finance & Budget Agent API",
        "status": "ok",
        "docs": "/docs",
        "ai_enabled": settings.ai_enabled,
    }


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
