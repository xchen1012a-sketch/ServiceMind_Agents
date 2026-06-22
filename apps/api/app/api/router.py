from fastapi import APIRouter

from app.api.routes import agent, approval, health, knowledge, mcp_tools, tickets

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(tickets.router)
api_router.include_router(agent.router)
api_router.include_router(knowledge.router)
api_router.include_router(mcp_tools.router)
api_router.include_router(approval.router)
