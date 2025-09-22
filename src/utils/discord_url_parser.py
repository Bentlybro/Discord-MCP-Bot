import re
from typing import Optional, Tuple
from urllib.parse import urlparse

class DiscordURLParser:
    """Parse Discord message URLs and extract IDs"""

    # Discord message URL pattern
    MESSAGE_URL_PATTERN = re.compile(
        r'https://discord\.com/channels/(?P<guild_id>\d+)/(?P<channel_id>\d+)/(?P<message_id>\d+)'
    )

    # Alternative discord.gg pattern (less common but exists)
    ALT_MESSAGE_URL_PATTERN = re.compile(
        r'https://(?:www\.)?discord\.gg/channels/(?P<guild_id>\d+)/(?P<channel_id>\d+)/(?P<message_id>\d+)'
    )

    @classmethod
    def parse_message_url(cls, url: str) -> Optional[Tuple[int, int, int]]:
        """
        Parse a Discord message URL and return (guild_id, channel_id, message_id)

        Args:
            url: Discord message URL

        Returns:
            Tuple of (guild_id, channel_id, message_id) or None if invalid
        """
        url = url.strip()

        # Try main pattern first
        match = cls.MESSAGE_URL_PATTERN.match(url)
        if not match:
            # Try alternative pattern
            match = cls.ALT_MESSAGE_URL_PATTERN.match(url)

        if match:
            try:
                guild_id = int(match.group('guild_id'))
                channel_id = int(match.group('channel_id'))
                message_id = int(match.group('message_id'))
                return (guild_id, channel_id, message_id)
            except ValueError:
                return None

        return None

    @classmethod
    def is_discord_message_url(cls, url: str) -> bool:
        """Check if a URL is a valid Discord message URL"""
        return cls.parse_message_url(url) is not None

    @classmethod
    def extract_ids_from_url(cls, url: str) -> dict:
        """
        Extract IDs from Discord URL and return as dictionary

        Returns:
            Dict with 'guild_id', 'channel_id', 'message_id' or empty dict if invalid
        """
        parsed = cls.parse_message_url(url)
        if parsed:
            guild_id, channel_id, message_id = parsed
            return {
                'guild_id': guild_id,
                'channel_id': channel_id,
                'message_id': message_id
            }
        return {}