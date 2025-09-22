from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import secrets
import string

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    discord_user_id = Column(String(20), unique=True, nullable=False)
    discord_username = Column(String(100), nullable=False)
    api_key = Column(String(64), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    last_used = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(48))

    def update_usage(self):
        """Update usage statistics"""
        self.last_used = datetime.utcnow()
        self.usage_count += 1