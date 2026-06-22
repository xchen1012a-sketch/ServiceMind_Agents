from fastapi import APIRouter

from app.api.routes import agent, health, knowledge, tickets

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(tickets.router)
api_router.include_router(agent.router)
api_router.include_router(knowledge.router)
