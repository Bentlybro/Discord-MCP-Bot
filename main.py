import asyncio
import logging
from fastapi import FastAPI
import uvicorn

from src.discord_bot.bot import DiscordBot
from src.mcp.protocol import MCPProtocolHandler
from src.api.routes import APIRoutes
from src.api.middleware import MiddlewareSetup
from src.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscordMCPServer:
    def __init__(self):
        self.app = FastAPI(title="Discord MCP Server", version="1.0.0")
        self.discord_bot = DiscordBot()
        self.mcp_handler = MCPProtocolHandler(self.discord_bot)

        # Setup middleware and routes
        self.middleware_setup = MiddlewareSetup(self.app)
        self.api_routes = APIRoutes(self.app, self.discord_bot, self.mcp_handler)

    async def run_discord_bot(self):
        """Run the Discord bot"""
        await self.discord_bot.start()

    async def run_api_server(self):
        """Run the FastAPI server"""
        config = uvicorn.Config(
            self.app,
            host=settings.api_host,
            port=settings.api_port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def start(self):
        """Start both Discord bot and API server"""
        logger.info("Starting Discord MCP Bot...")

        await asyncio.gather(
            self.run_discord_bot(),
            self.run_api_server()
        )

async def main():
    server = DiscordMCPServer()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())