from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
import logging

from ..models.discord_models import (
    MessageResponse, GetMessagesRequest, SearchMessagesRequest,
    SearchGuildMessagesRequest, ChannelInfo
)
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
                    "API key authentication",
                    "MCP protocol support",
                    "Discord message reading and searching"
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
                return await self.mcp_handler.handle_request(request)
            except Exception as e:
                logger.error(f"MCP handler error: {e}")
                # Return proper JSON-RPC error
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {"code": -32603, "message": str(e)}
                }

        # Optional: Keep REST endpoints for direct API access
        @self.app.post("/get_messages", response_model=List[MessageResponse])
        async def get_messages(
            request: GetMessagesRequest,
            user_id: str = Depends(verify_api_key)
        ):
            logger.info(f"REST API: get_messages from user {user_id}")
            result = await self.discord_bot.get_messages(
                int(request.channel_id),
                request.limit,
                request.before_message_id
            )

            if "error" in result:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=result["error"])

            return [MessageResponse(**msg) for msg in result["messages"]]

        @self.app.post("/search_messages", response_model=List[MessageResponse])
        async def search_messages(
            request: SearchMessagesRequest,
            user_id: str = Depends(verify_api_key)
        ):
            logger.info(f"REST API: search_messages from user {user_id}")
            result = await self.discord_bot.search_messages(
                int(request.channel_id),
                request.query,
                request.limit
            )

            if "error" in result:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=result["error"])

            return [MessageResponse(**msg) for msg in result["messages"]]

        @self.app.post("/search_guild_messages", response_model=List[MessageResponse])
        async def search_guild_messages(
            request: SearchGuildMessagesRequest,
            user_id: str = Depends(verify_api_key)
        ):
            logger.info(f"REST API: search_guild_messages from user {user_id}")
            result = await self.discord_bot.search_guild_messages(
                int(request.guild_id),
                request.query,
                request.limit
            )

            if "error" in result:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=result["error"])

            return [MessageResponse(**msg) for msg in result["messages"]]

        @self.app.get("/channels", response_model=List[ChannelInfo])
        async def list_channels(user_id: str = Depends(verify_api_key)):
            logger.info(f"REST API: list_channels from user {user_id}")
            result = self.discord_bot.list_channels()

            if "error" in result:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=result["error"])

            return [ChannelInfo(**ch) for ch in result["channels"]]