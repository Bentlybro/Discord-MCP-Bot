# MCP Setup Instructions

## 1. Configure MCP Server

Copy the example configuration:
```bash
cp mcp_config.example.json .mcp.json
```

Edit `.mcp.json` and replace:
- `your_api_key_here` with your actual API key from your `.env` file

## 2. Add to Claude Code

Add the new server:
```bash
claude mcp add discord-mcp-bot .mcp.json
```

## 3. Start the Server

Run your Discord MCP bot:
```bash
python main.py
```

## 4. Verify Connection

Check MCP server status:
```bash
claude mcp list
```

You should see:
```
discord-mcp-bot: http://0.0.0.0:8000 (HTTP) - ✓ Connected
```

## Available MCP Tools

Once connected, you can use these tools in Claude Code:

- `get_discord_messages` - Fetch recent messages from a channel
- `search_discord_messages` - Search messages in a specific channel
- `search_guild_messages` - Search messages across an entire guild
- `list_discord_channels` - List all accessible channels

## Example Usage

```
Get the last 10 messages from Discord channel "1234567890"
```

```
Search for messages containing "MCP" across guild "1234567890"
```