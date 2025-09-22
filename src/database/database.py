import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from typing import Optional
import logging

from .models import Base, User

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, database_url: str = "sqlite+aiosqlite:///discord_mcp.db"):
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")

    async def create_user(self, discord_user_id: str, discord_username: str) -> User:
        """Create a new user with API key"""
        async with self.async_session() as session:
            # Check if user already exists
            existing_user = await self.get_user_by_discord_id(discord_user_id)
            if existing_user:
                return existing_user

            api_key = User.generate_api_key()
            user = User(
                discord_user_id=discord_user_id,
                discord_username=discord_username,
                api_key=api_key
            )

            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"Created user: {discord_username} ({discord_user_id})")
            return user

    async def get_user_by_discord_id(self, discord_user_id: str) -> Optional[User]:
        """Get user by Discord ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.discord_user_id == discord_user_id)
            )
            return result.scalar_one_or_none()

    async def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Get user by API key"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.api_key == api_key, User.is_active == True)
            )
            return result.scalar_one_or_none()

    async def update_user_usage(self, api_key: str):
        """Update user usage statistics"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.api_key == api_key)
            )
            user = result.scalar_one_or_none()
            if user:
                user.update_usage()
                await session.commit()

    async def deactivate_user(self, discord_user_id: str) -> bool:
        """Deactivate a user's API access"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.discord_user_id == discord_user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.is_active = False
                await session.commit()
                return True
            return False

    async def regenerate_api_key(self, discord_user_id: str) -> Optional[str]:
        """Regenerate API key for a user"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.discord_user_id == discord_user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.api_key = User.generate_api_key()
                user.is_active = True
                await session.commit()
                return user.api_key
            return None

# Global database instance
db = Database()