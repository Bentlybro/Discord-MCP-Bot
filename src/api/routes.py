from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List

from ..models.discord_models import (
    MessageResponse, GetMessagesRequest, SearchMessagesRequest,
    SearchGuildMessagesRequest, ChannelInfo
)
from ..config.settings import settings

class APIRoutes:
    def __init__(self, app, discord_bot, mcp_handler):
        self.app = app
        self.discord_bot = discord_bot
        self.mcp_handler = mcp_handler
        self.security = HTTPBearer()
        self._setup_routes()

    def _verify_api_key(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
        """Verify API key for authentication"""
        if credentials.credentials != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return credentials

    def _setup_routes(self):
        @self.app.get("/", summary="Health check")
        async def root():
            return {
                "service": "Discord MCP Server",
                "status": "running",
                "bot_ready": self.discord_bot.is_ready(),
                "guilds": self.discord_bot.guild_count
            }

        @self.app.post("/", summary="MCP Protocol Handler")
        async def mcp_handler(request: dict):
            return await self.mcp_handler.handle_request(request)

        @self.app.post("/get_messages", response_model=List[MessageResponse])
        async def get_messages(
            request: GetMessagesRequest,
            credentials: HTTPAuthorizationCredentials = Depends(self._verify_api_key)
        ):
            try:
                result = await self.discord_bot.get_messages(
                    int(request.channel_id),
                    request.limit,
                    request.before_message_id
                )

                if "error" in result:
                    raise HTTPException(status_code=400, detail=result["error"])

                return [MessageResponse(**msg) for msg in result["messages"]]

            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid channel ID: {str(e)}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/search_messages", response_model=List[MessageResponse])
        async def search_messages(
            request: SearchMessagesRequest,
            credentials: HTTPAuthorizationCredentials = Depends(self._verify_api_key)
        ):
            try:
                result = await self.discord_bot.search_messages(
                    int(request.channel_id),
                    request.query,
                    request.limit
                )

                if "error" in result:
                    raise HTTPException(status_code=400, detail=result["error"])

                return [MessageResponse(**msg) for msg in result["messages"]]

            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid channel ID: {str(e)}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/search_guild_messages", response_model=List[MessageResponse])
        async def search_guild_messages(
            request: SearchGuildMessagesRequest,
            credentials: HTTPAuthorizationCredentials = Depends(self._verify_api_key)
        ):
            try:
                result = await self.discord_bot.search_guild_messages(
                    int(request.guild_id),
                    request.query,
                    request.limit
                )

                if "error" in result:
                    raise HTTPException(status_code=400, detail=result["error"])

                return [MessageResponse(**msg) for msg in result["messages"]]

            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid guild ID: {str(e)}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/channels", response_model=List[ChannelInfo])
        async def list_channels(
            credentials: HTTPAuthorizationCredentials = Depends(self._verify_api_key)
        ):
            try:
                result = self.discord_bot.list_channels()

                if "error" in result:
                    raise HTTPException(status_code=400, detail=result["error"])

                return [ChannelInfo(**ch) for ch in result["channels"]]

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))