# Discord MCP Bot

A Discord bot that exposes Discord API functionality through the Model Context Protocol (MCP), allowing AI assistants to read and search Discord messages.

## Project Structure

```
DiscordMCPBot/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py        # FastAPI route definitions
│   │   └── middleware.py    # CORS and rate limiting
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py      # Configuration management
│   ├── discord_bot/
│   │   ├── __init__.py
│   │   └── bot.py          # Discord bot logic
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── protocol.py     # MCP protocol handling
│   ├── models/
│   │   ├── __init__.py
│   │   └── discord_models.py # Pydantic models
│   └── __init__.py
├── main.py                 # Application entry point
├── rate_limiter.py        # Rate limiting utility
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── .mcp.json             # MCP configuration
```

## Features

- **Discord Message Reading**: Fetch recent messages from channels
- **Message Search**: Search for messages in specific channels or entire guilds
- **Channel Listing**: List all accessible Discord channels
- **MCP Protocol**: Full Model Context Protocol support for AI integration
- **REST API**: Traditional HTTP endpoints alongside MCP
- **Security**: API key authentication and rate limiting
- **Access Control**: Guild and channel restrictions

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Discord bot token and settings
   ```

3. **Add MCP server to Claude Code**:
   ```bash
   claude mcp add discord-mcp-bot .mcp.json
   ```

4. **Run the server**:
   ```bash
   python main.py
   ```

## Available Tools (MCP)

- `get_discord_messages` - Fetch recent messages from a channel
- `search_discord_messages` - Search messages in a specific channel
- `search_guild_messages` - Search messages across an entire guild
- `list_discord_channels` - List all accessible channels

## API Endpoints (HTTP)

- `GET /` - Health check
- `POST /` - MCP protocol handler
- `POST /get_messages` - Get channel messages
- `POST /search_messages` - Search channel messages
- `POST /search_guild_messages` - Search guild messages
- `GET /channels` - List channels

## Configuration

Set these environment variables in your `.env` file:

- `DISCORD_TOKEN` - Your Discord bot token
- `API_KEY` - API key for authentication
- `ALLOWED_GUILDS` - Comma-separated guild IDs (optional)
- `ALLOWED_CHANNELS` - Comma-separated channel IDs (optional)
- `API_HOST` - Server host (default: 0.0.0.0)
- `API_PORT` - Server port (default: 8000)