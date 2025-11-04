from fastapi import APIRouter

# Import available endpoints
from api.v1.endpoints import search, uploads

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])

# Future endpoints:
# from api.v1.endpoints import auth, users, conversations, projects
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
# api_router.include_router(projects.router, prefix="/projects", tags=["projects"])




