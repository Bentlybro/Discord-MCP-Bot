from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from .middleware import verify_api_key

logger = logging.getLogger(__name__)

class APIRoutes:
    def __init__(self, app, discord_bot, mcp_handler):
        self.app = app
        self.discord_bot = discord_bot
        self.mcp_handler = mcp_handler
        self.security = HTTPBearer()
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/", summary="Health check")
        async def root():
            return {
                "service": "Discord MCP Server",
                "status": "running",
                "bot_ready": self.discord_bot.is_ready(),
                "guilds": self.discord_bot.guild_count,
                "features": [
                    "User registration via Discord slash commands",
                    "Individual API key authentication per user",
                    "MCP protocol for AI assistant integration",
                    "Discord message reading and searching",
                    "Interactive conversations with Discord users",
                    "Message sending with user attribution",
                    "Thread support",
                    "User listing and discovery"
                ]
            }

        @self.app.get("/health", summary="Health check for monitoring")
        async def health_check():
            """Simple health check that doesn't require auth"""
            return {
                "status": "ok",
                "bot_ready": self.discord_bot.is_ready()
            }

        @self.app.post("/", summary="MCP Protocol Handler")
        async def mcp_handler(
            request: dict,
            credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())
        ):
            """Handle MCP protocol requests with user authentication"""
            try:
                # Verify API key
                user_id = await verify_api_key(credentials)
                logger.info(f"MCP request from user {user_id}: {request.get('method', 'unknown')}")
                return await self.mcp_handler.handle_request(request, user_id)
            except Exception as e:
                logger.error(f"MCP handler error: {e}")
                # Return proper JSON-RPC error
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {"code": -32603, "message": str(e)}
                }

