# Discord MCP Bot

**A Discord bot that exposes Discord API functionality through the Model Context Protocol (MCP), allowing AI assistants like Claude Code to read and search Discord messages.**

## Features

- **User Registration**: Discord slash commands for easy API key management (`/register`, `/mykey`, `/regenerate`, `/status`)
- **MCP Integration**: Full Model Context Protocol support for seamless AI assistant integration
- **Message Reading**: Fetch recent messages from Discord channels
- **Advanced Search**: Search messages within specific channels or across entire guilds/servers
- **Channel Discovery**: List all accessible Discord channels
- **Message Sending**: Send messages to Discord channels with optional reply support
- **Interactive Conversations**: Ask questions and wait for user responses in real-time
- **Secure Authentication**: Individual API keys per user with usage tracking
- **Hosted Service Ready**: Designed for multi-user deployment with database storage
- **Dual Interface**: Both MCP protocol and REST API endpoints
- **Modular Architecture**: Clean, maintainable codebase with separated concerns

<details>
<summary>Tech Stack</summary>

- **Python 3.8+**
- **Discord.py** - Discord API wrapper
- **FastAPI** - Modern web framework
- **Pydantic** - Data validation
- **Model Context Protocol** - AI integration standard

</details>

<details>
<summary>Project Structure</summary>

```
src/
├── api/          # FastAPI routes & middleware
├── config/       # Settings & configuration
├── discord_bot/  # Discord bot logic
├── mcp/          # MCP protocol handling
└── models/       # Pydantic data models
```

</details>

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Bentlybro/Discord-MCP-Bot
   cd Discord-MCP-Bot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Discord bot token and settings
   ```

4. **Run the server**:
   ```bash
   python main.py
   ```

## For Server Operators (Hosting)

If you want to host this MCP server for others to use:

1. **Deploy the server** on your domain/server
2. **Users register via Discord** - They use slash commands to get API keys
3. **Users connect via HTTP** - Using their personal API key

## For End Users (Connecting to a Hosted Server)

To connect to a hosted Discord MCP server:

1. **Join the Discord server** where the MCP bot is running

2. **Register for access** using Discord slash commands:
   ```
   /register
   ```
   The bot will send you a personal API key via DM or ephemeral message.

3. **Connect to the MCP server**:
   ```bash
   claude mcp add --transport http discord-mcp-bot http://server-domain.com:8000 --header "Authorization: Bearer YOUR_API_KEY_FROM_DISCORD_BOT"
   ```

   Replace:
   - `server-domain.com:8000` with the actual server URL
   - `YOUR_API_KEY_FROM_DISCORD_BOT` with the API key you received from the bot

4. **Manage your access**:
   - `/mykey` - Get your current API key
   - `/regenerate` - Generate a new API key (invalidates old one)
   - `/status` - Check your account status and usage

<details>
<summary>Available Tools (MCP)</summary>

- `get_discord_messages` - Fetch recent messages from a channel
- `search_discord_messages` - Search messages in a specific channel
- `search_guild_messages` - Search messages across an entire guild
- `get_message_by_url` - Get a specific message by Discord URL
- `list_discord_channels` - List all accessible channels
- `send_discord_message` - Send messages to Discord channels (with reply support)
- `ask_discord_question` - Send a question and wait for user responses (interactive conversations)
- `list_guild_users` - List all real users (not bots) in a specific guild
- `list_all_users` - List all real users (not bots) across all accessible guilds

</details>

<details>
<summary>API Endpoints (HTTP)</summary>

- `GET /` - Health check
- `POST /` - MCP protocol handler
- `POST /get_messages` - Get channel messages
- `POST /search_messages` - Search channel messages
- `POST /search_guild_messages` - Search guild messages
- `POST /get_message_by_url` - Get message by Discord URL
- `POST /send_message` - Send message to channel
- `POST /ask_question` - Send question and wait for reply
- `POST /list_guild_users` - List users in a specific guild
- `POST /list_all_users` - List users across all accessible guilds
- `GET /channels` - List channels

</details>

<details>
<summary>Configuration</summary>

Set these environment variables in your `.env` file:

- `DISCORD_TOKEN` - Your Discord bot token (required)
- `ALLOWED_GUILDS` - Comma-separated guild IDs (optional - restricts to specific servers)
- `ALLOWED_CHANNELS` - Comma-separated channel IDs (optional - restricts to specific channels)
- `API_HOST` - Server host (default: 0.0.0.0)
- `API_PORT` - Server port (default: 8000)

</details>

<details>
<summary>Documentation</summary>

- [Setup Instructions](MCP_SETUP.md)
- [Environment Configuration](.env.example)
- [MCP Configuration](mcp_config.example.json)

</details>

<details>
<summary>Use Cases</summary>

- **AI-Powered Discord Analysis**: Let Claude Code analyze your server conversations
- **Interactive Discord Bots**: Create AI assistants that can have real-time conversations
- **Message Retrieval**: Programmatically access Discord message history
- **Content Search**: Find specific discussions across channels
- **Server Management**: Automate Discord content analysis and moderation
- **Research & Analytics**: Extract insights from Discord communities
- **Customer Support**: AI agents that can ask clarifying questions and respond contextually

</details>

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Perfect for developers building AI-powered Discord tools and researchers analyzing Discord communities!**