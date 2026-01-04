"""
Access control utilities for Discord channels and guilds.
Handles permission checking based on configuration and Discord permissions.
"""
import discord
from typing import Optional

from ..config.settings import settings


class AccessChecker:
    """Handles access control checks for Discord resources"""

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

    def check_channel_access(self, channel_id: int) -> bool:
        """Check if bot has access to a specific channel or thread"""
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return False

        # For threads, check the parent channel permissions
        if isinstance(channel, discord.Thread):
            parent_channel = channel.parent
            if not parent_channel:
                return False

            # If allowed_channels is set, check parent channel
            if settings.allowed_channels:
                return parent_channel.id in settings.allowed_channels

            # If allowed_guilds is set, check guild
            if settings.allowed_guilds:
                return parent_channel.guild.id in settings.allowed_guilds
        else:
            # Regular channel access check
            if settings.allowed_channels:
                return channel_id in settings.allowed_channels

            if settings.allowed_guilds:
                return channel.guild.id in settings.allowed_guilds

        # If neither is set, allow all channels
        return True

    def check_guild_access(self, guild_id: int) -> bool:
        """Check if bot has access to a specific guild"""
        if settings.allowed_guilds and guild_id not in settings.allowed_guilds:
            return False
        return self.bot.get_guild(guild_id) is not None

    def can_read_channel(self, channel: discord.TextChannel) -> bool:
        """Check if bot can actually read messages in a channel"""
        if not channel.guild:
            return False
        permissions = channel.permissions_for(channel.guild.me)
        return permissions.read_messages and permissions.read_message_history

    def can_send_to_channel(self, channel: discord.TextChannel) -> bool:
        """Check if bot can send messages to a channel"""
        if not channel.guild:
            return False
        permissions = channel.permissions_for(channel.guild.me)
        return permissions.send_messages

    def is_channel_allowed(self, channel: discord.TextChannel) -> bool:
        """Check if channel is in the allowed list (config-based)"""
        if settings.allowed_channels:
            return channel.id in settings.allowed_channels
        return True

    def get_accessible_channel(self, channel_id: int) -> Optional[discord.TextChannel]:
        """Get a channel if bot has access, otherwise return None"""
        if not self.check_channel_access(channel_id):
            return None
        return self.bot.get_channel(channel_id)

    def get_accessible_guild(self, guild_id: int) -> Optional[discord.Guild]:
        """Get a guild if bot has access, otherwise return None"""
        if not self.check_guild_access(guild_id):
            return None
        return self.bot.get_guild(guild_id)
