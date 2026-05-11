"""
API Routes
"""
from fastapi import APIRouter

from app.api import auth, llm, results, tasks, works

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(works.router)
api_router.include_router(tasks.router)
api_router.include_router(results.router)
api_router.include_router(llm.router)
