import discord
import logging
from discord.ext import commands
from typing import List, Optional

from ..config.settings import settings

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