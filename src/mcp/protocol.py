"""
MCP Protocol Handler.
Handles JSON-RPC requests for the Model Context Protocol.
"""
import logging
from typing import Dict, Any, Optional

from .tools import MCP_TOOLS, MCP_SERVER_INFO, MCP_PROTOCOL_VERSION

logger = logging.getLogger(__name__)


class MCPProtocolHandler:
    def __init__(self, discord_bot):
        self.discord_bot = discord_bot

    def _success_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        """Build a successful JSON-RPC response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """Build a JSON-RPC error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message}
        }

    def _tool_result(self, request_id: Any, data: Any) -> Dict[str, Any]:
        """Build a tool call result response"""
        return self._success_response(request_id, {
            "content": [{"type": "text", "text": str(data)}]
        })

    async def handle_request(self, request: Dict[str, Any], requesting_user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle incoming MCP protocol requests"""
        method = request.get("method")
        request_id = request.get("id")

        try:
            if method == "initialize":
                return self._handle_initialize(request_id)
            elif method == "tools/list":
                return self._handle_tools_list(request_id)
            elif method == "tools/call":
                return await self._handle_tools_call(request, requesting_user_id)
            elif method == "notifications/initialized":
                return {}  # Just acknowledge the notification
            else:
                logger.warning(f"Unknown method: {method}")
                return self._error_response(request_id, -32601, f"Unknown method: {method}")
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return self._error_response(request_id, -32603, f"Internal error: {str(e)}")

    def _handle_initialize(self, request_id: Any) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        return self._success_response(request_id, {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": MCP_SERVER_INFO
        })

    def _handle_tools_list(self, request_id: Any) -> Dict[str, Any]:
        """Handle MCP tools/list request"""
        return self._success_response(request_id, {"tools": MCP_TOOLS})

    async def _handle_tools_call(self, request: Dict[str, Any], requesting_user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle MCP tools/call request"""
        request_id = request.get("id")
        tool_name = request["params"]["name"]
        args = request["params"].get("arguments", {})
        logger.info(f"Tool call: {tool_name}")

        # Dispatch to appropriate handler
        handler = self._get_tool_handler(tool_name)
        if handler:
            result = await handler(args, requesting_user_id)
            return self._tool_result(request_id, result)
        else:
            return self._error_response(request_id, -32602, f"Unknown tool: {tool_name}")

    def _get_tool_handler(self, tool_name: str):
        """Get the handler function for a tool"""
        handlers = {
            # Message reading
            "get_discord_messages": self._handle_get_messages,
            "search_discord_messages": self._handle_search_messages,
            "search_guild_messages": self._handle_search_guild_messages,
            "get_guild_activity_summary": self._handle_get_guild_activity_summary,
            "get_message_by_url": self._handle_get_message_by_url,
            "get_message_by_id": self._handle_get_message_by_id,
            "get_pinned_messages": self._handle_get_pinned_messages,
            "get_message_context": self._handle_get_message_context,
            "trace_reply_chain": self._handle_trace_reply_chain,
            # Message actions
            "send_discord_message": self._handle_send_message,
            "send_discord_file": self._handle_send_file,
            "ask_discord_question": self._handle_ask_question,
            "edit_message": self._handle_edit_message,
            "delete_message": self._handle_delete_message,
            "dm_user": self._handle_dm_user,
            # Channels & threads
            "list_discord_channels": self._handle_list_channels,
            "get_channel_info": self._handle_get_channel_info,
            "create_thread": self._handle_create_thread,
            # Users
            "list_guild_users": self._handle_list_guild_users,
            "list_all_users": self._handle_list_all_users,
            # Attachments
            "download_attachment": self._handle_download_attachment,
        }
        return handlers.get(tool_name)

    # Tool handlers
    async def _handle_get_messages(self, args: dict, user_id: str):
        return await self.discord_bot.get_messages(
            int(args["channel_id"]),
            args.get("limit", 10),
            args.get("before_message_id")
        )

    async def _handle_search_messages(self, args: dict, user_id: str):
        return await self.discord_bot.search_messages(
            int(args["channel_id"]),
            args["query"],
            args.get("limit", 10)
        )

    async def _handle_search_guild_messages(self, args: dict, user_id: str):
        return await self.discord_bot.search_guild_messages(
            int(args["guild_id"]),
            args["query"],
            args.get("limit", 50)
        )

    async def _handle_get_guild_activity_summary(self, args: dict, user_id: str):
        return await self.discord_bot.get_guild_activity_summary(
            int(args["guild_id"]),
            args.get("hours", 24)
        )

    async def _handle_get_message_by_url(self, args: dict, user_id: str):
        return await self.discord_bot.get_message_by_url(args["message_url"])

    async def _handle_get_message_by_id(self, args: dict, user_id: str):
        return await self.discord_bot.get_message_by_id(
            int(args["channel_id"]),
            args["message_id"]
        )

    async def _handle_trace_reply_chain(self, args: dict, user_id: str):
        return await self.discord_bot.trace_reply_chain(
            int(args["channel_id"]),
            args["message_id"],
            args.get("max_depth", 20)
        )

    async def _handle_list_channels(self, args: dict, user_id: str):
        return self.discord_bot.list_channels()

    async def _handle_get_channel_info(self, args: dict, user_id: str):
        return self.discord_bot.get_channel_info(int(args["channel_id"]))

    async def _handle_send_message(self, args: dict, user_id: str):
        return await self.discord_bot.send_message(
            int(args["channel_id"]),
            args["content"],
            args.get("reply_to_message_id"),
            user_id
        )

    async def _handle_send_file(self, args: dict, user_id: str):
        return await self.discord_bot.send_file(
            int(args["channel_id"]),
            args["filename"],
            args["file_content"],
            args.get("content"),
            args.get("reply_to_message_id"),
            user_id,
            args.get("is_base64", False)
        )

    async def _handle_ask_question(self, args: dict, user_id: str):
        return await self.discord_bot.wait_for_reply(
            int(args["channel_id"]),
            args["question"],
            args.get("timeout", 300),
            args.get("target_user_id"),
            user_id
        )

    async def _handle_list_guild_users(self, args: dict, user_id: str):
        return await self.discord_bot.list_guild_users(
            int(args["guild_id"]),
            args.get("include_bots", False)
        )

    async def _handle_list_all_users(self, args: dict, user_id: str):
        return await self.discord_bot.list_all_accessible_users(
            args.get("include_bots", False)
        )

    async def _handle_get_pinned_messages(self, args: dict, user_id: str):
        return await self.discord_bot.get_pinned_messages(
            int(args["channel_id"])
        )

    async def _handle_get_message_context(self, args: dict, user_id: str):
        return await self.discord_bot.get_message_context(
            int(args["channel_id"]),
            args["message_id"],
            args.get("before_count", 5),
            args.get("after_count", 5)
        )

    async def _handle_edit_message(self, args: dict, user_id: str):
        return await self.discord_bot.edit_message(
            int(args["channel_id"]),
            args["message_id"],
            args["new_content"]
        )

    async def _handle_delete_message(self, args: dict, user_id: str):
        return await self.discord_bot.delete_message(
            int(args["channel_id"]),
            args["message_id"]
        )

    async def _handle_create_thread(self, args: dict, user_id: str):
        return await self.discord_bot.create_thread(
            int(args["channel_id"]),
            args["name"],
            args.get("message_id"),
            args.get("auto_archive_duration", 1440)
        )

    async def _handle_dm_user(self, args: dict, user_id: str):
        return await self.discord_bot.dm_user(
            args["user_id"],
            args["content"],
            user_id
        )

    async def _handle_download_attachment(self, args: dict, user_id: str):
        return await self.discord_bot.download_attachment(
            int(args["channel_id"]),
            args["message_id"],
            args.get("attachment_index", 0)
        )
