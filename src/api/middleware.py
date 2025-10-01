from fastapi import HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from ..database.database import db
from ..config.settings import settings

logger = logging.getLogger(__name__)

class MiddlewareSetup:
    def __init__(self, app):
        self.app = app
        self.security = HTTPBearer()
        self._setup_cors()
        self._setup_auth_logging()

    def _setup_cors(self):
        """Setup CORS middleware with optional origin restrictions"""
        # If no allowed origins specified, allow all (for backward compatibility)
        # In production, you should specify allowed origins for security
        allowed_origins = settings.allowed_origins if settings.allowed_origins else ["*"]

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_auth_logging(self):
        """Setup authentication logging middleware"""
        @self.app.middleware("http")
        async def auth_logging_middleware(request: Request, call_next):
            # Log MCP requests for debugging
            if request.url.path in ["/", "/mcp"] and request.method == "POST":
                logger.debug(f"MCP request from {request.client.host}")

            response = await call_next(request)
            return response

async def verify_api_key(credentials: HTTPAuthorizationCredentials) -> str:
    """Verify API key and return user ID"""
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="API key required")

    user = await db.get_user_by_api_key(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Update usage stats
    await db.update_user_usage(credentials.credentials)

    return user.discord_user_id