import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
import os

from .models import Base, User, OAuthClient, AuthorizationCode, OAuthToken

logger = logging.getLogger(__name__)

# In-memory store for pending OAuth authorizations (short-lived)
_pending_auths: Dict[str, Dict[str, Any]] = {}

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
        """Get user by API key (expects plaintext API key, will hash and compare)

        Supports transparent migration from legacy SHA256 hashes to PBKDF2.
        If a user authenticates with a legacy hash, it will be automatically
        upgraded to PBKDF2.
        """
        async with self.async_session() as session:
            # First, try the new PBKDF2 hash
            api_key_hash = User.hash_api_key(api_key)
            result = await session.execute(
                select(User).where(
                    User.api_key_hash == api_key_hash,
                    User.is_active == True
                )
            )
            user = result.scalar_one_or_none()

            if user:
                return user

            # If not found, try the legacy SHA256 hash for migration
            legacy_hash = User.hash_api_key_legacy(api_key)
            result = await session.execute(
                select(User).where(
                    User.api_key_hash == legacy_hash,
                    User.is_active == True
                )
            )
            user = result.scalar_one_or_none()

            if user:
                # Transparently upgrade to PBKDF2 hash
                user.api_key_hash = api_key_hash
                await session.commit()
                logger.info(f"Migrated API key hash to PBKDF2 for user: {user.discord_user_id}")
                return user

            return None

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

    async def get_all_users(self):
        """Get all registered users"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).order_by(User.created_at.desc())
            )
            return result.scalars().all()

    # =========================================================================
    # OAuth Client Methods
    # =========================================================================

    async def create_oauth_client(
        self,
        client_id: str,
        client_name: str,
        redirect_uris: List[str]
    ) -> OAuthClient:
        """Create a new OAuth client"""
        async with self.async_session() as session:
            client = OAuthClient(
                client_id=client_id,
                client_name=client_name,
                redirect_uris=json.dumps(redirect_uris)
            )
            session.add(client)
            await session.commit()
            await session.refresh(client)
            logger.info(f"Created OAuth client: {client_name}")
            return client

    async def get_oauth_client(self, client_id: str) -> Optional[OAuthClient]:
        """Get OAuth client by client_id"""
        async with self.async_session() as session:
            result = await session.execute(
                select(OAuthClient).where(OAuthClient.client_id == client_id)
            )
            return result.scalar_one_or_none()

    # =========================================================================
    # Pending Auth Methods (in-memory for Discord OAuth flow)
    # =========================================================================

    async def store_pending_auth(
        self,
        auth_state: str,
        client_id: str,
        redirect_uri: Optional[str],
        scope: Optional[str],
        code_challenge: Optional[str],
        code_challenge_method: Optional[str],
        original_state: Optional[str]
    ):
        """Store pending authorization request"""
        _pending_auths[auth_state] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "original_state": original_state,
            "created_at": datetime.now(timezone.utc)
        }

    async def get_pending_auth(self, auth_state: str) -> Optional[Dict[str, Any]]:
        """Get pending authorization request"""
        return _pending_auths.get(auth_state)

    async def delete_pending_auth(self, auth_state: str):
        """Delete pending authorization request"""
        _pending_auths.pop(auth_state, None)

    # =========================================================================
    # Authorization Code Methods
    # =========================================================================

    async def create_authorization_code(
        self,
        code: str,
        client_id: str,
        user_id: int,
        redirect_uri: Optional[str],
        code_challenge: Optional[str],
        code_challenge_method: Optional[str],
        scope: Optional[str],
        expires_at: datetime
    ) -> AuthorizationCode:
        """Create a new authorization code"""
        async with self.async_session() as session:
            auth_code = AuthorizationCode(
                code=code,
                code_hash=AuthorizationCode.hash_code(code),
                client_id=client_id,
                user_id=user_id,
                redirect_uri=redirect_uri,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                scope=scope,
                expires_at=expires_at
            )
            session.add(auth_code)
            await session.commit()
            await session.refresh(auth_code)
            return auth_code

    async def get_authorization_code(self, code: str) -> Optional[AuthorizationCode]:
        """Get authorization code by plaintext code"""
        async with self.async_session() as session:
            code_hash = AuthorizationCode.hash_code(code)
            result = await session.execute(
                select(AuthorizationCode).where(
                    AuthorizationCode.code_hash == code_hash
                )
            )
            return result.scalar_one_or_none()

    async def mark_authorization_code_used(self, code: str):
        """Mark an authorization code as used"""
        async with self.async_session() as session:
            code_hash = AuthorizationCode.hash_code(code)
            result = await session.execute(
                select(AuthorizationCode).where(
                    AuthorizationCode.code_hash == code_hash
                )
            )
            auth_code = result.scalar_one_or_none()
            if auth_code:
                auth_code.used = True
                await session.commit()

    # =========================================================================
    # OAuth Token Methods
    # =========================================================================

    async def create_oauth_token(
        self,
        access_token: str,
        refresh_token: str,
        client_id: str,
        user_id: int,
        scope: Optional[str],
        expires_at: datetime,
        refresh_expires_at: datetime
    ) -> OAuthToken:
        """Create a new OAuth token"""
        async with self.async_session() as session:
            token = OAuthToken(
                access_token_hash=OAuthToken.hash_token(access_token),
                refresh_token_hash=OAuthToken.hash_token(refresh_token),
                client_id=client_id,
                user_id=user_id,
                scope=scope,
                expires_at=expires_at,
                refresh_expires_at=refresh_expires_at
            )
            session.add(token)
            await session.commit()
            await session.refresh(token)
            return token

    async def get_token_by_access_token(self, access_token: str) -> Optional[OAuthToken]:
        """Get token record by access token"""
        async with self.async_session() as session:
            token_hash = OAuthToken.hash_token(access_token)
            result = await session.execute(
                select(OAuthToken).where(
                    OAuthToken.access_token_hash == token_hash,
                    OAuthToken.revoked == False
                )
            )
            return result.scalar_one_or_none()

    async def get_token_by_refresh_token(self, refresh_token: str) -> Optional[OAuthToken]:
        """Get token record by refresh token"""
        async with self.async_session() as session:
            token_hash = OAuthToken.hash_token(refresh_token)
            result = await session.execute(
                select(OAuthToken).where(
                    OAuthToken.refresh_token_hash == token_hash,
                    OAuthToken.revoked == False
                )
            )
            return result.scalar_one_or_none()

    async def get_user_by_token(self, access_token: str) -> Optional[User]:
        """Get user associated with an OAuth access token"""
        token_record = await self.get_token_by_access_token(access_token)
        if not token_record:
            return None

        if token_record.is_expired() or token_record.revoked:
            return None

        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.id == token_record.user_id)
            )
            return result.scalar_one_or_none()

    async def revoke_token(self, token_id: int):
        """Revoke a token by ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(OAuthToken).where(OAuthToken.id == token_id)
            )
            token = result.scalar_one_or_none()
            if token:
                token.revoked = True
                await session.commit()

    async def revoke_token_by_value(self, token: str) -> bool:
        """Revoke a token by its value (access or refresh)"""
        token_hash = OAuthToken.hash_token(token)
        async with self.async_session() as session:
            # Try access token
            result = await session.execute(
                select(OAuthToken).where(OAuthToken.access_token_hash == token_hash)
            )
            token_record = result.scalar_one_or_none()

            if not token_record:
                # Try refresh token
                result = await session.execute(
                    select(OAuthToken).where(OAuthToken.refresh_token_hash == token_hash)
                )
                token_record = result.scalar_one_or_none()

            if token_record:
                token_record.revoked = True
                await session.commit()
                return True
            return False


# Global database instance
db = Database()