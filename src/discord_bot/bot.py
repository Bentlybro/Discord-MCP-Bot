import discord
import logging
from discord.ext import commands
from discord import app_commands
from typing import List, Optional

from ..config.settings import settings
from ..database.database import db

logger = logging.getLogger(__name__)

class DiscordBot:
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True

        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self._setup_events()

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            logger.info(f'{self.bot.user} has connected to Discord!')
            logger.info(f'Bot is in {len(self.bot.guilds)} guilds')

            # Initialize database
            await db.init_db()

            # Sync slash commands
            try:
                synced = await self.bot.tree.sync()
                logger.info(f"Synced {len(synced)} slash commands")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")

        # Add slash commands
        @self.bot.tree.command(name="register", description="Register for MCP API access")
        async def register_command(interaction: discord.Interaction):
            await self._handle_register(interaction)

        @self.bot.tree.command(name="mykey", description="Get your current API key")
        async def mykey_command(interaction: discord.Interaction):
            await self._handle_get_key(interaction)

        @self.bot.tree.command(name="regenerate", description="Regenerate your API key")
        async def regenerate_command(interaction: discord.Interaction):
            await self._handle_regenerate(interaction)

        @self.bot.tree.command(name="status", description="Check your account status")
        async def status_command(interaction: discord.Interaction):
            await self._handle_status(interaction)

    def check_channel_access(self, channel_id: int) -> bool:
        """Check if bot has access to a specific channel"""
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return False

        # If allowed_channels is set, use specific channel restrictions
        if settings.allowed_channels:
            return channel_id in settings.allowed_channels

        # If allowed_guilds is set, allow any channel in those guilds
        if settings.allowed_guilds:
            return channel.guild.id in settings.allowed_guilds

        # If neither is set, allow all channels (be careful with this!)
        return True

    async def get_messages(self, channel_id: int, limit: int = 10, before_message_id: Optional[str] = None) -> dict:
        """Get recent messages from a channel"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            messages = []
            before = None
            if before_message_id:
                before = discord.Object(id=int(before_message_id))

            async for message in channel.history(limit=limit, before=before):
                messages.append({
                    "id": str(message.id),
                    "author": message.author.display_name,
                    "author_id": str(message.author.id),
                    "content": message.content,
                    "timestamp": message.created_at.isoformat(),
                    "channel_id": str(message.channel.id),
                    "channel_name": message.channel.name,
                    "guild_id": str(message.guild.id),
                    "guild_name": message.guild.name
                })

            return {"messages": messages}
        except Exception as e:
            return {"error": str(e)}

    async def search_messages(self, channel_id: int, query: str, limit: int = 10) -> dict:
        """Search for messages in a specific channel"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            messages = []
            count = 0

            async for message in channel.history(limit=1000):
                if count >= limit:
                    break

                if query.lower() in message.content.lower():
                    messages.append({
                        "id": str(message.id),
                        "author": message.author.display_name,
                        "author_id": str(message.author.id),
                        "content": message.content,
                        "timestamp": message.created_at.isoformat(),
                        "channel_id": str(message.channel.id),
                        "channel_name": message.channel.name,
                        "guild_id": str(message.guild.id),
                        "guild_name": message.guild.name
                    })
                    count += 1

            return {"messages": messages}
        except Exception as e:
            return {"error": str(e)}

    async def search_guild_messages(self, guild_id: int, query: str, limit: int = 50) -> dict:
        """Search for messages across all channels in a guild"""
        try:
            # Check if we have access to this guild
            if settings.allowed_guilds and guild_id not in settings.allowed_guilds:
                return {"error": "Access denied to this guild"}

            guild = self.bot.get_guild(guild_id)
            if not guild:
                return {"error": "Guild not found"}

            messages = []
            total_found = 0

            # Search through all accessible text channels in the guild
            for channel in guild.text_channels:
                if total_found >= limit:
                    break

                # Check channel access (respects allowed_channels if set)
                if settings.allowed_channels and channel.id not in settings.allowed_channels:
                    continue

                try:
                    # Search in each channel (limit per channel to avoid overwhelming)
                    channel_limit = min(500, limit - total_found)
                    async for message in channel.history(limit=channel_limit):
                        if total_found >= limit:
                            break

                        if query.lower() in message.content.lower():
                            messages.append({
                                "id": str(message.id),
                                "author": message.author.display_name,
                                "author_id": str(message.author.id),
                                "content": message.content,
                                "timestamp": message.created_at.isoformat(),
                                "channel_id": str(message.channel.id),
                                "channel_name": message.channel.name,
                                "guild_id": str(message.guild.id),
                                "guild_name": message.guild.name
                            })
                            total_found += 1

                except discord.Forbidden:
                    # Skip channels we don't have permission to read
                    continue
                except Exception as e:
                    logger.warning(f"Error searching channel {channel.name}: {str(e)}")
                    continue

            return {
                "messages": messages,
                "total_found": total_found,
                "channels_searched": len([ch for ch in guild.text_channels if not settings.allowed_channels or ch.id in settings.allowed_channels]),
                "query": query,
                "guild_name": guild.name
            }
        except Exception as e:
            return {"error": str(e)}

    def list_channels(self) -> dict:
        """List all accessible Discord channels"""
        try:
            channels = []

            for guild in self.bot.guilds:
                # If allowed_guilds is set, only include those guilds
                if settings.allowed_guilds and guild.id not in settings.allowed_guilds:
                    continue

                for channel in guild.text_channels:
                    # If allowed_channels is set, only include those specific channels
                    if settings.allowed_channels and channel.id not in settings.allowed_channels:
                        continue

                    channels.append({
                        "id": str(channel.id),
                        "name": channel.name,
                        "type": "text",
                        "guild_id": str(guild.id),
                        "guild_name": guild.name
                    })

            return {"channels": channels}
        except Exception as e:
            return {"error": str(e)}

    async def start(self):
        """Start the Discord bot"""
        await self.bot.start(settings.discord_token)

    def is_ready(self) -> bool:
        """Check if bot is ready"""
        return self.bot.is_ready()

    @property
    def guild_count(self) -> int:
        """Get number of guilds bot is in"""
        return len(self.bot.guilds) if self.bot.is_ready() else 0

    async def _handle_register(self, interaction: discord.Interaction):
        """Handle /register command"""
        try:
            user_id = str(interaction.user.id)
            username = str(interaction.user)

            # Check if user already exists
            existing_user = await db.get_user_by_discord_id(user_id)
            if existing_user:
                await interaction.response.send_message(
                    "✅ You're already registered! Use `/mykey` to get your API key.",
                    ephemeral=True
                )
                return

            # Create new user
            user = await db.create_user(user_id, username)

            # Create connection instructions
            server_url = f"http://{settings.api_host}:{settings.api_port}"
            if settings.api_host == "0.0.0.0":
                server_url = f"http://your-domain.com:{settings.api_port}"

            instructions = f"""🎉 **Registration Successful!**

**Your API Key:** ||`{user.api_key}`|| (click to reveal)

**To connect with Claude Code:**
```bash
claude mcp add --transport http discord-mcp-bot {server_url} --header "Authorization: Bearer {user.api_key}"
```

**Available MCP Tools:**
• `get_discord_messages` - Fetch recent messages
• `search_discord_messages` - Search in specific channels
• `search_guild_messages` - Search entire servers
• `list_discord_channels` - List accessible channels

⚠️ **Keep your API key secure!** Use `/regenerate` if it's compromised."""

            # Try to DM first, fallback to ephemeral
            try:
                await interaction.user.send(instructions)
                await interaction.response.send_message(
                    "✅ Registration complete! Check your DMs for your API key and setup instructions.",
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(instructions, ephemeral=True)

        except Exception as e:
            logger.error(f"Registration error: {e}")
            await interaction.response.send_message(
                "❌ Registration failed. Please try again later.",
                ephemeral=True
            )

    async def _handle_get_key(self, interaction: discord.Interaction):
        """Handle /mykey command"""
        try:
            user = await db.get_user_by_discord_id(str(interaction.user.id))
            if not user:
                await interaction.response.send_message(
                    "❌ You're not registered yet. Use `/register` first.",
                    ephemeral=True
                )
                return

            server_url = f"http://{settings.api_host}:{settings.api_port}"
            if settings.api_host == "0.0.0.0":
                server_url = f"http://your-domain.com:{settings.api_port}"

            message = f"""🔑 **Your API Key:** ||`{user.api_key}`|| (click to reveal)

**Connection Command:**
```bash
claude mcp add --transport http discord-mcp-bot {server_url} --header "Authorization: Bearer {user.api_key}"
```"""

            # Try DM first, fallback to ephemeral
            try:
                await interaction.user.send(message)
                await interaction.response.send_message(
                    "✅ API key sent to your DMs!",
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(message, ephemeral=True)

        except Exception as e:
            logger.error(f"Get key error: {e}")
            await interaction.response.send_message(
                "❌ Failed to retrieve API key.",
                ephemeral=True
            )

    async def _handle_regenerate(self, interaction: discord.Interaction):
        """Handle /regenerate command"""
        try:
            new_key = await db.regenerate_api_key(str(interaction.user.id))
            if not new_key:
                await interaction.response.send_message(
                    "❌ You're not registered yet. Use `/register` first.",
                    ephemeral=True
                )
                return

            server_url = f"http://{settings.api_host}:{settings.api_port}"
            if settings.api_host == "0.0.0.0":
                server_url = f"http://your-domain.com:{settings.api_port}"

            message = f"""🔄 **New API Key Generated:** ||`{new_key}`|| (click to reveal)

⚠️ **Your old key is now invalid!**

**Updated Connection Command:**
```bash
claude mcp remove discord-mcp-bot
claude mcp add --transport http discord-mcp-bot {server_url} --header "Authorization: Bearer {new_key}"
```"""

            # Try DM first, fallback to ephemeral
            try:
                await interaction.user.send(message)
                await interaction.response.send_message(
                    "✅ New API key generated and sent to your DMs!",
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(message, ephemeral=True)

        except Exception as e:
            logger.error(f"Regenerate error: {e}")
            await interaction.response.send_message(
                "❌ Failed to regenerate API key.",
                ephemeral=True
            )

    async def _handle_status(self, interaction: discord.Interaction):
        """Handle /status command"""
        try:
            user = await db.get_user_by_discord_id(str(interaction.user.id))
            if not user:
                await interaction.response.send_message(
                    "❌ You're not registered yet. Use `/register` first.",
                    ephemeral=True
                )
                return

            status_emoji = "✅" if user.is_active else "❌"
            last_used = user.last_used.strftime("%Y-%m-%d %H:%M UTC") if user.last_used else "Never"

            status_msg = f"""📊 **Account Status**

**Status:** {status_emoji} {"Active" if user.is_active else "Inactive"}
**Username:** {user.discord_username}
**Created:** {user.created_at.strftime("%Y-%m-%d %H:%M UTC")}
**Last Used:** {last_used}
**Usage Count:** {user.usage_count} requests

**Commands:**
• `/mykey` - Get your API key
• `/regenerate` - Generate new API key
• `/register` - Register (if needed)"""

            await interaction.response.send_message(status_msg, ephemeral=True)

        except Exception as e:
            logger.error(f"Status error: {e}")
            await interaction.response.send_message(
                "❌ Failed to get status.",
                ephemeral=True
            )