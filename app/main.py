from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import auth, users, courses, sections, media, attachments, enrollment, payments, reviews, search, notifications, websocket, certificates
from app.core.websocket_manager import ws_manager
from app.core.config import settings

app = FastAPI(
    title="Online Course Platform",
    description="Production-grade course platform API",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(courses.router, prefix="/api/v1")
app.include_router(sections.router, prefix="/api/v1")
app.include_router(media.router, prefix="/api/v1")
app.include_router(attachments.router, prefix="/api/v1")
app.include_router(enrollment.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(certificates.router, prefix="/api/v1")
app.include_router(websocket.router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "env": settings.app_env}


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    return {"status": "ready"}