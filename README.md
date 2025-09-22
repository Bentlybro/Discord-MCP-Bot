# Discord MCP Bot

**A Discord bot that exposes Discord API functionality through the Model Context Protocol (MCP), allowing AI assistants like Claude Code to read and search Discord messages.**

## Features

- **MCP Integration**: Full Model Context Protocol support for seamless AI assistant integration
- **Message Reading**: Fetch recent messages from Discord channels
- **Advanced Search**: Search messages within specific channels or across entire guilds/servers
- **Channel Discovery**: List all accessible Discord channels
- **Security**: API key authentication and access control
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

4. **Setup MCP configuration**:
   ```bash
   cp mcp_config.example.json .mcp.json
   # Edit .mcp.json with your API key
   ```

5. **Run the server**:
   ```bash
   python main.py
   ```

6. **Add to Claude Code**:
   ```bash
   claude mcp add discord-mcp-bot .mcp.json
   ```

<details>
<summary>Available Tools (MCP)</summary>

- `get_discord_messages` - Fetch recent messages from a channel
- `search_discord_messages` - Search messages in a specific channel
- `search_guild_messages` - Search messages across an entire guild
- `list_discord_channels` - List all accessible channels

</details>

<details>
<summary>API Endpoints (HTTP)</summary>

- `GET /` - Health check
- `POST /` - MCP protocol handler
- `POST /get_messages` - Get channel messages
- `POST /search_messages` - Search channel messages
- `POST /search_guild_messages` - Search guild messages
- `GET /channels` - List channels

</details>

<details>
<summary>Configuration</summary>

Set these environment variables in your `.env` file:

- `DISCORD_TOKEN` - Your Discord bot token
- `API_KEY` - API key for authentication
- `ALLOWED_GUILDS` - Comma-separated guild IDs (optional)
- `ALLOWED_CHANNELS` - Comma-separated channel IDs (optional)
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
- **Message Retrieval**: Programmatically access Discord message history
- **Content Search**: Find specific discussions across channels
- **Server Management**: Automate Discord content analysis and moderation
- **Research & Analytics**: Extract insights from Discord communities

</details>

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Perfect for developers building AI-powered Discord tools and researchers analyzing Discord communities!**