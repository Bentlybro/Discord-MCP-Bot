from fastapi import Security, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
import logging
import json

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
            }

        @self.app.get("/health", summary="Health check for monitoring")
        async def health_check():
            """Simple health check that doesn't require auth"""
            return {
                "status": "ok",
                "bot_ready": self.discord_bot.is_ready()
            }

        @self.app.get("/mcp", summary="MCP SSE Endpoint")
        async def mcp_sse_endpoint(
            request: Request,
            credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())
        ):
            """Handle MCP SSE streaming endpoint (optional GET support)"""
            try:
                # Verify API key
                user_id = await verify_api_key(credentials)

                # Validate Origin header for security
                origin = request.headers.get("origin")
                if origin:
                    logger.info(f"MCP GET request from origin: {origin}")

                # Check Accept header
                accept = request.headers.get("accept", "")
                if "text/event-stream" not in accept:
                    return Response(
                        content="Method Not Allowed - SSE not requested",
                        status_code=405,
                        headers={"Allow": "POST"}
                    )

                # For now, return 405 as SSE streaming is optional
                # You can implement full SSE support later if needed
                return Response(
                    content="SSE streaming not implemented - use POST for requests",
                    status_code=405,
                    headers={"Allow": "POST"}
                )
            except Exception as e:
                logger.error(f"MCP SSE handler error: {e}")
                return Response(content=str(e), status_code=403)

        @self.app.post("/mcp", summary="MCP Protocol Handler")
        async def mcp_handler(
            mcp_request: dict,
            request: Request,
            credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())
        ):
            """Handle MCP protocol requests with user authentication"""
            try:
                # Validate Origin header for security
                origin = request.headers.get("origin")
                if origin:
                    logger.info(f"MCP request from origin: {origin}")

                # Verify API key
                user_id = await verify_api_key(credentials)
                logger.info(f"MCP request from user {user_id}: {mcp_request.get('method', 'unknown')}")

                # Handle the MCP request
                response_data = await self.mcp_handler.handle_request(mcp_request, user_id)

                # Check if this is a notification (no id field) - return 202
                if "id" not in mcp_request or mcp_request.get("method") == "notifications/initialized":
                    return Response(
                        content=json.dumps(response_data),
                        status_code=202,
                        media_type="application/json"
                    )

                # Regular request - return 200
                return response_data

            except Exception as e:
                logger.error(f"MCP handler error: {e}")
                # Return proper JSON-RPC error
                error_response = {
                    "jsonrpc": "2.0",
                    "id": mcp_request.get("id"),
                    "error": {"code": -32603, "message": str(e)}
                }
                return Response(
                    content=json.dumps(error_response),
                    status_code=200,  # JSON-RPC errors still use 200
                    media_type="application/json"
                )

