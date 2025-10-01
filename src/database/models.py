from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import secrets
import string
import hashlib

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    discord_user_id = Column(String(20), unique=True, nullable=False)
    discord_username = Column(String(100), nullable=False)
    api_key_hash = Column(String(64), unique=True, nullable=False)  # SHA256 hash
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    last_used = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key with dmcp- prefix"""
        alphabet = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(48))
        return f'dmcp-{random_part}'

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key using SHA256"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def update_usage(self):
        """Update usage statistics"""
        self.last_used = datetime.utcnow()
        self.usage_count += 1