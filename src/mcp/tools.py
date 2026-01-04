"""
MCP Tool Definitions.
Defines all available tools for the MCP protocol.
"""

MCP_TOOLS = [
    {
        "name": "get_discord_messages",
        "description": "Fetch recent messages from a Discord channel",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "limit": {"type": "integer", "description": "Number of messages to fetch (default: 10)"},
                "before_message_id": {"type": "string", "description": "Fetch messages before this message ID"}
            },
            "required": ["channel_id"]
        }
    },
    {
        "name": "search_discord_messages",
        "description": "Search for messages containing specific text in a channel",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "query": {"type": "string", "description": "Text to search for"},
                "limit": {"type": "integer", "description": "Max results to return (default: 10)"}
            },
            "required": ["channel_id", "query"]
        }
    },
    {
        "name": "search_guild_messages",
        "description": "Search for messages containing specific text across all channels in a guild",
        "inputSchema": {
            "type": "object",
            "properties": {
                "guild_id": {"type": "string", "description": "The Discord guild/server ID"},
                "query": {"type": "string", "description": "Text to search for"},
                "limit": {"type": "integer", "description": "Max results to return (default: 50)"}
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
                "message_url": {"type": "string", "description": "Full Discord message URL"}
            },
            "required": ["message_url"]
        }
    },
    {
        "name": "list_discord_channels",
        "description": "List all accessible Discord channels the bot can read",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "send_discord_message",
        "description": "Send a message to a Discord channel",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "content": {"type": "string", "description": "Message content to send"},
                "reply_to_message_id": {"type": "string", "description": "Message ID to reply to (optional)"}
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
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "question": {"type": "string", "description": "Question to ask"},
                "timeout": {"type": "integer", "description": "Seconds to wait for reply (default: 300)"},
                "target_user_id": {"type": "string", "description": "Only accept replies from this user ID"}
            },
            "required": ["channel_id", "question"]
        }
    },
    {
        "name": "list_guild_users",
        "description": "List all users in a specific Discord guild",
        "inputSchema": {
            "type": "object",
            "properties": {
                "guild_id": {"type": "string", "description": "The Discord guild/server ID"},
                "include_bots": {"type": "boolean", "description": "Include bot accounts (default: false)"}
            },
            "required": ["guild_id"]
        }
    },
    {
        "name": "list_all_users",
        "description": "List all users across all accessible guilds",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_bots": {"type": "boolean", "description": "Include bot accounts (default: false)"}
            }
        }
    }
]


# Server info for MCP initialize response
MCP_SERVER_INFO = {
    "name": "discord-mcp-bot",
    "version": "1.0.0"
}

MCP_PROTOCOL_VERSION = "2024-11-05"
