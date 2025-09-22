# Discord MCP Bot

A Discord bot that exposes an MCP (Model Context Protocol) compatible API, allowing Claude and other LLMs to read messages from Discord servers.

## Features

- **Message Reading**: Fetch recent messages from Discord channels
- **Message Search**: Search for messages containing specific text
- **Channel Listing**: Get available channels the bot has access to
- **Security**: API key authentication and rate limiting
- **Access Control**: Restrict access to specific guilds and channels

## API Endpoints

### GET /
Health check endpoint that returns bot status.

### POST /get_messages
Fetch recent messages from a Discord channel.

**Request Body:**
```json
{
  "channel_id": "123456789012345678",
  "limit": 10,
  "before_message_id": "987654321098765432"
}
```

**Response:**
```json
[
  {
    "id": "message_id",
    "author": "display_name",
    "author_id": "user_id",
    "content": "message content",
    "timestamp": "2023-12-01T10:30:00.000Z",
    "channel_id": "channel_id",
    "channel_name": "channel_name",
    "guild_id": "guild_id",
    "guild_name": "guild_name"
  }
]
```

### POST /search_messages
Search for messages containing specific text.

**Request Body:**
```json
{
  "channel_id": "123456789012345678",
  "query": "search term",
  "limit": 10
}
```

### GET /channels
List all accessible channels.

## Setup Instructions

### 1. Discord Bot Setup

1. Go to https://discord.com/developers/applications
2. Create a new application
3. Go to the "Bot" section
4. Create a bot and copy the token
5. Enable the following bot permissions:
   - Read Messages/View Channels
   - Read Message History
6. Enable the following privileged gateway intents:
   - Message Content Intent
7. Invite the bot to your server with the required permissions

### 2. Installation

```bash
# Clone or download this repository
cd DiscordMCPBot

# Install dependencies
pip install -r requirements.txt

# Copy the environment template
cp .env.example .env
```

### 3. Configuration

Edit the `.env` file with your settings:

```env
DISCORD_TOKEN=your_bot_token_here
API_KEY=your_secure_api_key_here
ALLOWED_GUILDS=guild_id_1,guild_id_2
ALLOWED_CHANNELS=channel_id_1,channel_id_2
API_HOST=127.0.0.1
API_PORT=8000
```

**Configuration Options:**
- `DISCORD_TOKEN`: Your Discord bot token
- `API_KEY`: A secure key for API authentication
- `ALLOWED_GUILDS`: Comma-separated list of guild IDs (optional, empty = all guilds)
- `ALLOWED_CHANNELS`: Comma-separated list of channel IDs (optional, empty = all channels)
- `API_HOST`: API server host (default: 127.0.0.1)
- `API_PORT`: API server port (default: 8000)

### 4. Running the Bot

```bash
python discord_mcp_bot.py
```

The bot will start both the Discord client and the API server.

## Using with Claude

### Authentication

All API requests require the `Authorization` header:
```
Authorization: Bearer your_api_key_here
```

### Rate Limiting

- 100 requests per minute per IP address
- Rate limit information is included in error responses

### Example Usage

```bash
# Get recent messages
curl -X POST "http://127.0.0.1:8000/get_messages" \
  -H "Authorization: Bearer your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"channel_id": "123456789012345678", "limit": 5}'

# Search messages
curl -X POST "http://127.0.0.1:8000/search_messages" \
  -H "Authorization: Bearer your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"channel_id": "123456789012345678", "query": "hello", "limit": 5}'

# List channels
curl -X GET "http://127.0.0.1:8000/channels" \
  -H "Authorization: Bearer your_api_key_here"
```

## Security Considerations

1. **API Key**: Use a strong, unique API key
2. **Access Control**: Limit `ALLOWED_GUILDS` and `ALLOWED_CHANNELS` to only what's necessary
3. **Network**: Consider running behind a reverse proxy with HTTPS in production
4. **Rate Limiting**: Built-in rate limiting helps prevent abuse
5. **Discord Permissions**: Only grant the minimum required Discord permissions

## Troubleshooting

### Bot Not Connecting
- Verify the Discord token is correct
- Ensure the bot has been invited to the server
- Check that required intents are enabled

### API Access Issues
- Verify the API key matches your configuration
- Check that the channel/guild IDs are in your allowed lists
- Ensure the bot has permission to read the target channels

### Rate Limiting
- Default limit is 100 requests per minute per IP
- Wait for the reset time or adjust the rate limit settings

## License

This project is open source. Use responsibly and in accordance with Discord's Terms of Service.