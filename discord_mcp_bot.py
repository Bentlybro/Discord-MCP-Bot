import os
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

import discord
from discord.ext import commands
from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from rate_limiter import RateLimiter

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageResponse(BaseModel):
    id: str
    author: str
    author_id: str
    content: str
    timestamp: str
    channel_id: str
    channel_name: str
    guild_id: str
    guild_name: str

class GetMessagesRequest(BaseModel):
    channel_id: str
    limit: int = 10
    before_message_id: Optional[str] = None

class SearchMessagesRequest(BaseModel):
    channel_id: str
    query: str
    limit: int = 10

class ChannelInfo(BaseModel):
    id: str
    name: str
    type: str
    guild_id: str
    guild_name: str

class DiscordMCPBot:
    def __init__(self):
        self.discord_token = os.getenv("DISCORD_TOKEN")
        self.api_key = os.getenv("API_KEY", "default-secure-key")
        self.allowed_guilds = self._parse_ids(os.getenv("ALLOWED_GUILDS", ""))
        self.allowed_channels = self._parse_ids(os.getenv("ALLOWED_CHANNELS", ""))
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))

        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True

        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.app = FastAPI(title="Discord MCP Server", version="1.0.0")
        self.security = HTTPBearer()
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self._setup_discord_events()
        self._setup_api_routes()
        self._setup_middleware()

    def _parse_ids(self, ids_string: str) -> List[int]:
        if not ids_string:
            return []
        return [int(id_str.strip()) for id_str in ids_string.split(",") if id_str.strip()]

    def _setup_discord_events(self):
        @self.bot.event
        async def on_ready():
            logger.info(f'{self.bot.user} has connected to Discord!')
            logger.info(f'Bot is in {len(self.bot.guilds)} guilds')

    def _verify_api_key(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
        if credentials.credentials != self.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return credentials

    def _check_channel_access(self, channel_id: int) -> bool:
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return False

        # If allowed_channels is set, use specific channel restrictions
        if self.allowed_channels:
            return channel_id in self.allowed_channels

        # If allowed_guilds is set, allow any channel in those guilds
        if self.allowed_guilds:
            return channel.guild.id in self.allowed_guilds

        # If neither is set, allow all channels (be careful with this!)
        return True

    def _setup_middleware(self):
        @self.app.middleware("http")
        async def rate_limit_middleware(request: Request, call_next):
            if request.url.path not in ["/", "/docs", "/openapi.json"]:
                client_ip = request.client.host
                if not self.rate_limiter.is_allowed(client_ip):
                    remaining = self.rate_limiter.get_remaining_requests(client_ip)
                    reset_time = self.rate_limiter.get_reset_time(client_ip)
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Remaining: {remaining}, Reset at: {reset_time}"
                    )

            response = await call_next(request)
            return response

    def _setup_api_routes(self):
        @self.app.get("/", summary="Health check")
        async def root():
            return {
                "service": "Discord MCP Server",
                "status": "running",
                "bot_ready": self.bot.is_ready(),
                "guilds": len(self.bot.guilds) if self.bot.is_ready() else 0
            }

        @self.app.post("/", summary="MCP Protocol Handler")
        async def mcp_handler(request: dict):
            # Handle MCP protocol messages
            logger.info(f"Received MCP request: {request}")
            method = request.get("method")

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "discord-mcp-bot",
                            "version": "1.0.0"
                        }
                    }
                }
                logger.info(f"Sending initialize response: {response}")
                return response

            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "tools": [
                        {
                            "name": "get_discord_messages",
                            "description": "Fetch recent messages from a Discord channel",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "channel_id": {"type": "string"},
                                    "limit": {"type": "integer"},
                                    "before_message_id": {"type": "string"}
                                },
                                "required": ["channel_id"]
                            }
                        },
                        {
                            "name": "search_discord_messages",
                            "description": "Search for messages containing specific text",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "channel_id": {"type": "string"},
                                    "query": {"type": "string"},
                                    "limit": {"type": "integer"}
                                },
                                "required": ["channel_id", "query"]
                            }
                        },
                        {
                            "name": "list_discord_channels",
                            "description": "List all accessible Discord channels",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "search_guild_messages",
                            "description": "Search for messages containing specific text across all channels in a guild",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "guild_id": {"type": "string"},
                                    "query": {"type": "string"},
                                    "limit": {"type": "integer"}
                                },
                                "required": ["guild_id", "query"]
                            }
                        }
                        ]
                    }
                }
                logger.info(f"Sending tools/list response: {response}")
                return response

            elif method == "tools/call":
                tool_name = request["params"]["name"]
                args = request["params"]["arguments"]
                logger.info(f"Tool call: {tool_name} with args: {args}")

                result_data = None
                if tool_name == "get_discord_messages":
                    result_data = await self._get_messages_internal(args)
                elif tool_name == "search_discord_messages":
                    result_data = await self._search_messages_internal(args)
                elif tool_name == "search_guild_messages":
                    result_data = await self._search_guild_messages_internal(args)
                elif tool_name == "list_discord_channels":
                    result_data = await self._list_channels_internal()

                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [{"type": "text", "text": str(result_data)}]
                    }
                }
                logger.info(f"Tool response: {response}")
                return response

            elif method == "notifications/initialized":
                # Just acknowledge the notification
                return {}

            logger.error(f"Unknown method: {method}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            }

        @self.app.post("/get_messages", response_model=List[MessageResponse])
        async def get_messages(
            request: GetMessagesRequest,
            credentials: HTTPAuthorizationCredentials = Depends(self._verify_api_key)
        ):
            try:
                channel_id = int(request.channel_id)

                if not self._check_channel_access(channel_id):
                    raise HTTPException(status_code=403, detail="Access denied to this channel")

                channel = self.bot.get_channel(channel_id)
                if not channel:
                    raise HTTPException(status_code=404, detail="Channel not found")

                messages = []
                before = None
                if request.before_message_id:
                    before = discord.Object(id=int(request.before_message_id))

                async for message in channel.history(limit=request.limit, before=before):
                    messages.append(MessageResponse(
                        id=str(message.id),
                        author=message.author.display_name,
                        author_id=str(message.author.id),
                        content=message.content,
                        timestamp=message.created_at.isoformat(),
                        channel_id=str(message.channel.id),
                        channel_name=message.channel.name,
                        guild_id=str(message.guild.id),
                        guild_name=message.guild.name
                    ))

                return messages

            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid channel ID: {str(e)}")
            except Exception as e:
                logger.error(f"Error getting messages: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/search_messages", response_model=List[MessageResponse])
        async def search_messages(
            request: SearchMessagesRequest,
            credentials: HTTPAuthorizationCredentials = Depends(self._verify_api_key)
        ):
            try:
                channel_id = int(request.channel_id)

                if not self._check_channel_access(channel_id):
                    raise HTTPException(status_code=403, detail="Access denied to this channel")

                channel = self.bot.get_channel(channel_id)
                if not channel:
                    raise HTTPException(status_code=404, detail="Channel not found")

                messages = []
                count = 0

                async for message in channel.history(limit=1000):
                    if count >= request.limit:
                        break

                    if request.query.lower() in message.content.lower():
                        messages.append(MessageResponse(
                            id=str(message.id),
                            author=message.author.display_name,
                            author_id=str(message.author.id),
                            content=message.content,
                            timestamp=message.created_at.isoformat(),
                            channel_id=str(message.channel.id),
                            channel_name=message.channel.name,
                            guild_id=str(message.guild.id),
                            guild_name=message.guild.name
                        ))
                        count += 1

                return messages

            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid channel ID: {str(e)}")
            except Exception as e:
                logger.error(f"Error searching messages: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/channels", response_model=List[ChannelInfo])
        async def list_channels(
            credentials: HTTPAuthorizationCredentials = Depends(self._verify_api_key)
        ):
            try:
                channels = []

                for guild in self.bot.guilds:
                    # If allowed_guilds is set, only include those guilds
                    if self.allowed_guilds and guild.id not in self.allowed_guilds:
                        continue

                    for channel in guild.text_channels:
                        # If allowed_channels is set, only include those specific channels
                        if self.allowed_channels and channel.id not in self.allowed_channels:
                            continue

                        channels.append(ChannelInfo(
                            id=str(channel.id),
                            name=channel.name,
                            type="text",
                            guild_id=str(guild.id),
                            guild_name=guild.name
                        ))

                return channels

            except Exception as e:
                logger.error(f"Error listing channels: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

    async def _get_messages_internal(self, args):
        """Internal method for MCP message fetching"""
        try:
            channel_id = int(args["channel_id"])
            limit = args.get("limit", 10)
            before_message_id = args.get("before_message_id")

            if not self._check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            messages = []
            before = None
            if before_message_id:
                before = discord.Object(id=int(before_message_id))

            async for message in channel.history(limit=limit, before=before):
                messages.append({
                    "id": str(message.id),
                    "author": message.author.display_name,
                    "author_id": str(message.author.id),
                    "content": message.content,
                    "timestamp": message.created_at.isoformat(),
                    "channel_id": str(message.channel.id),
                    "channel_name": message.channel.name,
                    "guild_id": str(message.guild.id),
                    "guild_name": message.guild.name
                })

            return {"messages": messages}
        except Exception as e:
            return {"error": str(e)}

    async def _search_messages_internal(self, args):
        """Internal method for MCP message searching"""
        try:
            channel_id = int(args["channel_id"])
            query = args["query"]
            limit = args.get("limit", 10)

            if not self._check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            messages = []
            count = 0

            async for message in channel.history(limit=1000):
                if count >= limit:
                    break

                if query.lower() in message.content.lower():
                    messages.append({
                        "id": str(message.id),
                        "author": message.author.display_name,
                        "author_id": str(message.author.id),
                        "content": message.content,
                        "timestamp": message.created_at.isoformat(),
                        "channel_id": str(message.channel.id),
                        "channel_name": message.channel.name,
                        "guild_id": str(message.guild.id),
                        "guild_name": message.guild.name
                    })
                    count += 1

            return {"messages": messages}
        except Exception as e:
            return {"error": str(e)}

    async def _search_guild_messages_internal(self, args):
        """Internal method for MCP guild-wide message searching"""
        try:
            guild_id = int(args["guild_id"])
            query = args["query"]
            limit = args.get("limit", 50)  # Higher default for guild search

            # Check if we have access to this guild
            if self.allowed_guilds and guild_id not in self.allowed_guilds:
                return {"error": "Access denied to this guild"}

            guild = self.bot.get_guild(guild_id)
            if not guild:
                return {"error": "Guild not found"}

            messages = []
            total_found = 0

            # Search through all accessible text channels in the guild
            for channel in guild.text_channels:
                if total_found >= limit:
                    break

                # Check channel access (respects allowed_channels if set)
                if self.allowed_channels and channel.id not in self.allowed_channels:
                    continue

                try:
                    # Search in each channel (limit per channel to avoid overwhelming)
                    channel_limit = min(500, limit - total_found)
                    async for message in channel.history(limit=channel_limit):
                        if total_found >= limit:
                            break

                        if query.lower() in message.content.lower():
                            messages.append({
                                "id": str(message.id),
                                "author": message.author.display_name,
                                "author_id": str(message.author.id),
                                "content": message.content,
                                "timestamp": message.created_at.isoformat(),
                                "channel_id": str(message.channel.id),
                                "channel_name": message.channel.name,
                                "guild_id": str(message.guild.id),
                                "guild_name": message.guild.name
                            })
                            total_found += 1

                except discord.Forbidden:
                    # Skip channels we don't have permission to read
                    continue
                except Exception as e:
                    logger.warning(f"Error searching channel {channel.name}: {str(e)}")
                    continue

            return {
                "messages": messages,
                "total_found": total_found,
                "channels_searched": len([ch for ch in guild.text_channels if not self.allowed_channels or ch.id in self.allowed_channels]),
                "query": query,
                "guild_name": guild.name
            }
        except Exception as e:
            return {"error": str(e)}

    async def _list_channels_internal(self):
        """Internal method for MCP channel listing"""
        try:
            channels = []

            for guild in self.bot.guilds:
                # If allowed_guilds is set, only include those guilds
                if self.allowed_guilds and guild.id not in self.allowed_guilds:
                    continue

                for channel in guild.text_channels:
                    # If allowed_channels is set, only include those specific channels
                    if self.allowed_channels and channel.id not in self.allowed_channels:
                        continue

                    channels.append({
                        "id": str(channel.id),
                        "name": channel.name,
                        "type": "text",
                        "guild_id": str(guild.id),
                        "guild_name": guild.name
                    })

            return {"channels": channels}
        except Exception as e:
            return {"error": str(e)}

    async def run_bot(self):
        await self.bot.start(self.discord_token)

    async def run_api(self):
        config = uvicorn.Config(
            self.app,
            host=self.api_host,
            port=self.api_port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def start(self):
        logger.info("Starting Discord MCP Bot...")

        await asyncio.gather(
            self.run_bot(),
            self.run_api()
        )

async def main():
    bot = DiscordMCPBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())