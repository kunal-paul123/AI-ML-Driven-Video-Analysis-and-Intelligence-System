from fastapi import APIRouter
from app.api.v1 import cameras, alerts, analytics, auth

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(cameras.router)
api_router.include_router(alerts.router)
api_router.include_router(analytics.router)
