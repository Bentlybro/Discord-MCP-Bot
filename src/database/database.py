import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from typing import Optional
import logging
import os

from .models import Base, User

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, database_url: str = "sqlite+aiosqlite:///db/discord_mcp.db"):
        # Ensure db directory exists
        os.makedirs("db", exist_ok=True)

        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")

    async def create_user(self, discord_user_id: str, discord_username: str) -> tuple[User, str]:
        """Create a new user with API key

        Returns:
            tuple[User, str]: The user object (with hashed key) and the plaintext API key
        """
        async with self.async_session() as session:
            # Check if user already exists
            existing_user = await self.get_user_by_discord_id(discord_user_id)
            if existing_user:
                # Return existing user but no plaintext key (they need to regenerate)
                return existing_user, None

            # Generate plaintext API key
            plaintext_api_key = User.generate_api_key()

            # Hash the API key before storing
            hashed_api_key = User.hash_api_key(plaintext_api_key)

            user = User(
                discord_user_id=discord_user_id,
                discord_username=discord_username,
                api_key_hash=hashed_api_key
            )

            session.add(user)
            await session.commit()
            await session.refresh(user)

            logger.info(f"Created user: {discord_username} ({discord_user_id})")
            return user, plaintext_api_key

    async def get_user_by_discord_id(self, discord_user_id: str) -> Optional[User]:
        """Get user by Discord ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.discord_user_id == discord_user_id)
            )
            return result.scalar_one_or_none()

    async def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Get user by API key (expects plaintext API key, will hash and compare)"""
        async with self.async_session() as session:
            # Hash the provided API key
            api_key_hash = User.hash_api_key(api_key)

            # Look up user by hash
            result = await session.execute(
                select(User).where(
                    User.api_key_hash == api_key_hash,
                    User.is_active == True
                )
            )
            return result.scalar_one_or_none()

    async def update_user_usage(self, api_key: str):
        """Update user usage statistics"""
        # Get user by API key (which hashes internally)
        user = await self.get_user_by_api_key(api_key)
        if user:
            async with self.async_session() as session:
                # Merge the user object into this session
                user = await session.merge(user)
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
        """Regenerate API key for a user

        Returns:
            str: The new plaintext API key, or None if user not found
        """
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.discord_user_id == discord_user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                # Generate new plaintext API key
                plaintext_api_key = User.generate_api_key()

                # Hash before storing
                hashed_api_key = User.hash_api_key(plaintext_api_key)

                user.api_key_hash = hashed_api_key
                user.is_active = True
                await session.commit()

                logger.info(f"Regenerated API key for user: {discord_user_id}")
                # Return plaintext key to user (only time they'll see it)
                return plaintext_api_key
            return None

# Global database instance
db = Database()