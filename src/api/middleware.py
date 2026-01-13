from fastapi import HTTPException, Request, Response
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


def get_www_authenticate_header() -> str:
    """Get the WWW-Authenticate header value for 401 responses"""
    base_url = settings.public_domain.rstrip('/')
    return f'Bearer resource="{base_url}/.well-known/oauth-protected-resource"'


async def verify_bearer_token(credentials: HTTPAuthorizationCredentials) -> str:
    """
    Verify bearer token (either API key or OAuth access token).
    Returns the user's Discord ID.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization required",
            headers={"WWW-Authenticate": get_www_authenticate_header()}
        )

    token = credentials.credentials

    # First, try as an OAuth access token
    user = await db.get_user_by_token(token)
    if user:
        return user.discord_user_id

    # Fall back to API key authentication
    user = await db.get_user_by_api_key(token)
    if user:
        # Update usage stats for API key
        await db.update_user_usage(token)
        return user.discord_user_id

    # Neither worked
    raise HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": get_www_authenticate_header()}
    )


# Alias for backward compatibility
async def verify_api_key(credentials: HTTPAuthorizationCredentials) -> str:
    """Verify API key or OAuth token and return user ID"""
    return await verify_bearer_token(credentials)