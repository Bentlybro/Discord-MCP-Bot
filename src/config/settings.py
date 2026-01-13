import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.discord_token = os.getenv("DISCORD_TOKEN")
        self.allowed_guilds = self._parse_ids(os.getenv("ALLOWED_GUILDS", ""))
        self.allowed_channels = self._parse_ids(os.getenv("ALLOWED_CHANNELS", ""))
        self.allowed_origins = self._parse_list(os.getenv("ALLOWED_ORIGINS", ""))
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.public_domain = os.getenv("PUBLIC_DOMAIN", f"http://{self.api_host}:{self.api_port}")

        # Discord OAuth settings (for user authentication)
        self.discord_client_id = os.getenv("DISCORD_CLIENT_ID", "")
        self.discord_client_secret = os.getenv("DISCORD_CLIENT_SECRET", "")

        # OAuth server settings
        self.oauth_token_expiry_hours = int(os.getenv("OAUTH_TOKEN_EXPIRY_HOURS", "24"))
        self.oauth_refresh_token_expiry_days = int(os.getenv("OAUTH_REFRESH_TOKEN_EXPIRY_DAYS", "30"))
        self.oauth_code_expiry_minutes = int(os.getenv("OAUTH_CODE_EXPIRY_MINUTES", "10"))

    def _parse_ids(self, ids_string: str) -> List[int]:
        if not ids_string:
            return []
        return [int(id_str.strip()) for id_str in ids_string.split(",") if id_str.strip()]

    def _parse_list(self, list_string: str) -> List[str]:
        """Parse comma-separated string list"""
        if not list_string:
            return []
        return [item.strip() for item in list_string.split(",") if item.strip()]

# Global settings instance
settings = Settings()