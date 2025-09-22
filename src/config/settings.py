import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.discord_token = os.getenv("DISCORD_TOKEN")
        self.allowed_guilds = self._parse_ids(os.getenv("ALLOWED_GUILDS", ""))
        self.allowed_channels = self._parse_ids(os.getenv("ALLOWED_CHANNELS", ""))
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))

    def _parse_ids(self, ids_string: str) -> List[int]:
        if not ids_string:
            return []
        return [int(id_str.strip()) for id_str in ids_string.split(",") if id_str.strip()]

# Global settings instance
settings = Settings()