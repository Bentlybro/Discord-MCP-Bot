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
    },
    {
        "name": "get_pinned_messages",
        "description": "Get all pinned messages from a Discord channel",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"}
            },
            "required": ["channel_id"]
        }
    },
    {
        "name": "get_message_context",
        "description": "Get messages before and after a specific message for context",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "message_id": {"type": "string", "description": "The message ID to get context around"},
                "before_count": {"type": "integer", "description": "Number of messages before (default: 5)"},
                "after_count": {"type": "integer", "description": "Number of messages after (default: 5)"}
            },
            "required": ["channel_id", "message_id"]
        }
    },
    {
        "name": "edit_message",
        "description": "Edit a message that the bot previously sent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "message_id": {"type": "string", "description": "The message ID to edit"},
                "new_content": {"type": "string", "description": "The new message content"}
            },
            "required": ["channel_id", "message_id", "new_content"]
        }
    },
    {
        "name": "delete_message",
        "description": "Delete a message that the bot previously sent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "message_id": {"type": "string", "description": "The message ID to delete"}
            },
            "required": ["channel_id", "message_id"]
        }
    },
    {
        "name": "create_thread",
        "description": "Create a new thread from a message or as a standalone thread in a channel",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "name": {"type": "string", "description": "Name for the new thread"},
                "message_id": {"type": "string", "description": "Message ID to create thread from (optional - if not provided, creates standalone thread)"},
                "auto_archive_duration": {"type": "integer", "description": "Minutes until auto-archive: 60, 1440, 4320, or 10080 (default: 1440)"}
            },
            "required": ["channel_id", "name"]
        }
    },
    {
        "name": "dm_user",
        "description": "Send a direct message to a Discord user",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "The Discord user ID to DM"},
                "content": {"type": "string", "description": "Message content to send"}
            },
            "required": ["user_id", "content"]
        }
    },
    {
        "name": "download_attachment",
        "description": "Download an attachment from a Discord message and return its content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "message_id": {"type": "string", "description": "The message ID containing the attachment"},
                "attachment_index": {"type": "integer", "description": "Index of attachment if multiple (default: 0)"}
            },
            "required": ["channel_id", "message_id"]
        }
    }
]


# Server info for MCP initialize response
MCP_SERVER_INFO = {
    "name": "discord-mcp-bot",
    "version": "1.0.0"
}

MCP_PROTOCOL_VERSION = "2024-11-05"
