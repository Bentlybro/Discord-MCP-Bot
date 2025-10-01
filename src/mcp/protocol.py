import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MCPProtocolHandler:
    def __init__(self, discord_bot):
        self.discord_bot = discord_bot

    async def handle_request(self, request: Dict[str, Any], requesting_user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle incoming MCP protocol requests"""
        method = request.get("method")

        try:
            if method == "initialize":
                return self._handle_initialize(request)
            elif method == "tools/list":
                return self._handle_tools_list(request)
            elif method == "tools/call":
                return await self._handle_tools_call(request, requesting_user_id)
            elif method == "notifications/initialized":
                return {}  # Just acknowledge the notification
            else:
                logger.warning(f"Unknown method: {method}")
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {"code": -32601, "message": f"Unknown method: {method}"}
                }
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
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
                    },
                    {
                        "name": "get_message_by_url",
                        "description": "Get a specific Discord message by its URL",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message_url": {"type": "string"}
                            },
                            "required": ["message_url"]
                        }
                    },
                    {
                        "name": "send_discord_message",
                        "description": "Send a message to a Discord channel",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "channel_id": {"type": "string"},
                                "content": {"type": "string"},
                                "reply_to_message_id": {"type": "string"}
                            },
                            "required": ["channel_id", "content"]
                        }
                    },
                    {
                        "name": "ask_discord_question",
                        "description": "Send a question to Discord and wait for a reply (interactive conversation)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "channel_id": {"type": "string"},
                                "question": {"type": "string"},
                                "timeout": {"type": "integer"},
                                "target_user_id": {"type": "string"}
                            },
                            "required": ["channel_id", "question"]
                        }
                    },
                    {
                        "name": "list_guild_users",
                        "description": "List all real users (not bots) in a specific Discord guild",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "guild_id": {"type": "string"},
                                "include_bots": {"type": "boolean"}
                            },
                            "required": ["guild_id"]
                        }
                    },
                    {
                        "name": "list_all_users",
                        "description": "List all real users (not bots) across all accessible guilds",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "include_bots": {"type": "boolean"}
                            }
                        }
                    }
                ]
            }
        }
        return response

    async def _handle_tools_call(self, request: Dict[str, Any], requesting_user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle MCP tools/call request"""
        tool_name = request["params"]["name"]
        args = request["params"]["arguments"]
        logger.info(f"Tool call: {tool_name}")

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
        elif tool_name == "get_message_by_url":
            result_data = await self.discord_bot.get_message_by_url(args["message_url"])
        elif tool_name == "send_discord_message":
            result_data = await self.discord_bot.send_message(
                int(args["channel_id"]),
                args["content"],
                args.get("reply_to_message_id"),
                requesting_user_id
            )
        elif tool_name == "ask_discord_question":
            result_data = await self.discord_bot.wait_for_reply(
                int(args["channel_id"]),
                args["question"],
                args.get("timeout", 300),
                args.get("target_user_id"),
                requesting_user_id
            )
        elif tool_name == "list_guild_users":
            result_data = await self.discord_bot.list_guild_users(
                int(args["guild_id"]),
                args.get("include_bots", False)
            )
        elif tool_name == "list_all_users":
            result_data = await self.discord_bot.list_all_accessible_users(
                args.get("include_bots", False)
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
        return response