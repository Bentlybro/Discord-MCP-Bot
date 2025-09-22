import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MCPProtocolHandler:
    def __init__(self, discord_bot):
        self.discord_bot = discord_bot

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP protocol requests"""
        logger.info(f"Received MCP request: {request}")
        method = request.get("method")

        if method == "initialize":
            return self._handle_initialize(request)
        elif method == "tools/list":
            return self._handle_tools_list(request)
        elif method == "tools/call":
            return await self._handle_tools_call(request)
        elif method == "notifications/initialized":
            return {}  # Just acknowledge the notification
        else:
            logger.error(f"Unknown method: {method}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            }

    def _handle_initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request"""
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

    def _handle_tools_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tools/list request"""
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

    async def _handle_tools_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tools/call request"""
        tool_name = request["params"]["name"]
        args = request["params"]["arguments"]
        logger.info(f"Tool call: {tool_name} with args: {args}")

        result_data = None
        if tool_name == "get_discord_messages":
            result_data = await self.discord_bot.get_messages(
                int(args["channel_id"]),
                args.get("limit", 10),
                args.get("before_message_id")
            )
        elif tool_name == "search_discord_messages":
            result_data = await self.discord_bot.search_messages(
                int(args["channel_id"]),
                args["query"],
                args.get("limit", 10)
            )
        elif tool_name == "search_guild_messages":
            result_data = await self.discord_bot.search_guild_messages(
                int(args["guild_id"]),
                args["query"],
                args.get("limit", 50)
            )
        elif tool_name == "list_discord_channels":
            result_data = self.discord_bot.list_channels()

        response = {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "content": [{"type": "text", "text": str(result_data)}]
            }
        }
        logger.info(f"Tool response: {response}")
        return response