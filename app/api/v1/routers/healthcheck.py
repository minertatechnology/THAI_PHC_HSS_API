from fastapi import APIRouter
from datetime import datetime, timezone


healthcheck_router = APIRouter(prefix="/health", tags=["health"])

@healthcheck_router.get("/")
def healthcheck():
     return {
           "status": "healthy",
           "timestamp": datetime.now(timezone.utc),
           "version": "1.0.0"
       }

