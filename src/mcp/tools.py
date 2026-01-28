"""
MCP Tool Definitions.
Defines all available tools for the MCP protocol.
"""

MCP_TOOLS = [
    # ========== Reading Messages ==========
    {
        "name": "get_discord_messages",
        "description": "Fetch recent messages from a Discord channel. Returns messages in reverse chronological order (newest first). IMPORTANT: Start with a small limit (10-20) to avoid flooding your context. Use 'before_message_id' pagination to fetch more messages incrementally if needed - pass the oldest message's ID to get the next batch.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "limit": {"type": "integer", "description": "Number of messages to fetch. Start small (10-20), use pagination for more. Default: 10, max: 100"},
                "before_message_id": {"type": "string", "description": "Fetch messages older than this message ID. Use the oldest message's ID from previous results to paginate backwards through history"}
            },
            "required": ["channel_id"]
        }
    },
    {
        "name": "get_message_by_url",
        "description": "Get a specific Discord message by its URL. Use this when someone shares a Discord message link. Returns full message details including attachments and reactions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message_url": {"type": "string", "description": "Full Discord message URL (e.g., https://discord.com/channels/123/456/789)"}
            },
            "required": ["message_url"]
        }
    },
    {
        "name": "get_pinned_messages",
        "description": "Get all pinned messages from a channel. Pinned messages often contain important information like rules, links, or key decisions.",
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
        "description": "Get messages before and after a specific message. Useful for understanding the full conversation around a particular message.",
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
        "name": "get_message_by_id",
        "description": "Get a specific message by its ID. Simpler than get_message_by_url when you already have the channel and message IDs. Returns full message details including attachments and reactions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "message_id": {"type": "string", "description": "The message ID to fetch"}
            },
            "required": ["channel_id", "message_id"]
        }
    },
    {
        "name": "trace_reply_chain",
        "description": "Trace back through a chain of message replies. Given a message that is a reply, this follows the reply_to references back to build the full conversation thread. Perfect for understanding back-and-forth conversations where people reply to each other with unrelated messages in between.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "message_id": {"type": "string", "description": "The message ID to start tracing from (usually the latest message in a thread)"},
                "max_depth": {"type": "integer", "description": "Maximum number of replies to trace back (default: 20, max: 50)"}
            },
            "required": ["channel_id", "message_id"]
        }
    },

    # ========== Searching ==========
    {
        "name": "search_discord_messages",
        "description": "Search for messages containing specific text in a single channel. Case-insensitive. Good for finding discussions about a specific topic. Also searches within forum channel threads.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID to search in"},
                "query": {"type": "string", "description": "Text to search for (case-insensitive)"},
                "limit": {"type": "integer", "description": "Max results to return. Keep small to preserve context (default: 10)"}
            },
            "required": ["channel_id", "query"]
        }
    },
    {
        "name": "search_guild_messages",
        "description": "Search for messages across ALL channels in a server, including forum threads. Use this when you don't know which channel contains the information. More comprehensive but slower than single-channel search.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "guild_id": {"type": "string", "description": "The Discord server/guild ID"},
                "query": {"type": "string", "description": "Text to search for (case-insensitive)"},
                "limit": {"type": "integer", "description": "Max total results. Keep reasonable to preserve context (default: 50, max: 50)"}
            },
            "required": ["guild_id", "query"]
        }
    },
    {
        "name": "get_guild_activity_summary",
        "description": "Get a lightweight activity summary for all channels in a server. Returns message counts, participant lists, and last activity times WITHOUT full message content. Use this FIRST to scout server activity before diving into specific channels. Much more context-efficient than fetching messages directly.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "guild_id": {"type": "string", "description": "The Discord server/guild ID"},
                "hours": {"type": "integer", "description": "Time window to analyze in hours (default: 24). Use smaller values like 6-12 for very active servers."}
            },
            "required": ["guild_id"]
        }
    },

    # ========== Channels & Threads ==========
    {
        "name": "list_discord_channels",
        "description": "List all Discord channels, forums, and threads the bot can access. Use this first to discover available channels and get their IDs. Returns text channels, forum channels (with their posts/threads), and active threads. Only shows channels the bot has read permissions for.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_channel_info",
        "description": "Get detailed information about a channel including its topic/description, type, category, and settings. Channel topics often contain important context or links.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"}
            },
            "required": ["channel_id"]
        }
    },
    {
        "name": "create_thread",
        "description": "Create a new thread for focused discussion. Can create from an existing message (to discuss that topic) or as a standalone thread in a channel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "name": {"type": "string", "description": "Name for the new thread"},
                "message_id": {"type": "string", "description": "Create thread from this message (optional - omit for standalone thread)"},
                "auto_archive_duration": {"type": "integer", "description": "Minutes until auto-archive: 60 (1hr), 1440 (24hr), 4320 (3d), 10080 (7d). Default: 1440"}
            },
            "required": ["channel_id", "name"]
        }
    },

    # ========== Sending Messages ==========
    {
        "name": "send_discord_message",
        "description": "Send a message to a Discord channel. Supports replying to a specific message. Messages include attribution showing which user's Claude sent it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "content": {"type": "string", "description": "Message content (supports Discord markdown)"},
                "reply_to_message_id": {"type": "string", "description": "Message ID to reply to (creates a reply thread)"}
            },
            "required": ["channel_id", "content"]
        }
    },
    {
        "name": "send_discord_file",
        "description": "Send a file to a Discord channel. Use for sharing reports, code files, logs, data exports, or any file up to 25MB. For text files, send content directly. For binary files (images, PDFs), base64-encode the content and set is_base64=true. Messages include attribution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "filename": {"type": "string", "description": "Name for the file including extension (e.g., 'report.md', 'data.json', 'image.png')"},
                "file_content": {"type": "string", "description": "File content - plain text for text files, or base64-encoded string for binary files"},
                "content": {"type": "string", "description": "Optional message text to accompany the file"},
                "reply_to_message_id": {"type": "string", "description": "Message ID to reply to (optional)"},
                "is_base64": {"type": "boolean", "description": "Set to true if file_content is base64-encoded binary data (e.g., for images, PDFs). Default: false (plain text)"}
            },
            "required": ["channel_id", "filename", "file_content"]
        }
    },
    {
        "name": "ask_discord_question",
        "description": "Send a question and wait for a reply. Use this for interactive conversations where you need a response before continuing. Blocks until someone replies or timeout.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "question": {"type": "string", "description": "Question to ask"},
                "timeout": {"type": "integer", "description": "Seconds to wait for reply (default: 300 = 5 minutes)"},
                "target_user_id": {"type": "string", "description": "Only accept replies from this specific user"}
            },
            "required": ["channel_id", "question"]
        }
    },
    {
        "name": "dm_user",
        "description": "Send a direct message to a user. Use for private communication. Will fail if user has DMs disabled. Messages include attribution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "The Discord user ID to DM"},
                "content": {"type": "string", "description": "Message content"}
            },
            "required": ["user_id", "content"]
        }
    },
    {
        "name": "edit_message",
        "description": "Edit a message that this bot previously sent. Cannot edit messages from other users.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "message_id": {"type": "string", "description": "The message ID to edit (must be bot's own message)"},
                "new_content": {"type": "string", "description": "The new message content"}
            },
            "required": ["channel_id", "message_id", "new_content"]
        }
    },
    {
        "name": "delete_message",
        "description": "Delete a message that this bot previously sent. Cannot delete messages from other users. Use for cleanup.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "message_id": {"type": "string", "description": "The message ID to delete (must be bot's own message)"}
            },
            "required": ["channel_id", "message_id"]
        }
    },

    # ========== Users ==========
    {
        "name": "list_guild_users",
        "description": "List all users in a Discord server. Returns usernames, display names, status, and roles. Use to find user IDs for DMs or mentions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "guild_id": {"type": "string", "description": "The Discord server/guild ID"},
                "include_bots": {"type": "boolean", "description": "Include bot accounts (default: false)"}
            },
            "required": ["guild_id"]
        }
    },
    {
        "name": "list_all_users",
        "description": "List all users across all accessible servers. Deduplicates users who are in multiple servers. Good for finding a user when you don't know which server they're in.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_bots": {"type": "boolean", "description": "Include bot accounts (default: false)"}
            }
        }
    },

    # ========== Attachments ==========
    {
        "name": "download_attachment",
        "description": "Download a file attachment from a message. Returns text content directly for text/code files, or base64-encoded data for binary files. Max 10MB. Use to read shared code, logs, or config files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "The Discord channel ID"},
                "message_id": {"type": "string", "description": "The message ID containing the attachment"},
                "attachment_index": {"type": "integer", "description": "Which attachment if multiple (0-indexed, default: 0)"}
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
