from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import secrets
import string
import hashlib

Base = declarative_base()


class OAuthClient(Base):
    """Registered OAuth clients (Claude Code, Claude Desktop, etc.)"""
    __tablename__ = "oauth_clients"

    id = Column(Integer, primary_key=True)
    client_id = Column(String(64), unique=True, nullable=False, index=True)
    client_name = Column(String(100), nullable=True)
    redirect_uris = Column(Text, nullable=True)  # JSON array of redirect URIs
    created_at = Column(DateTime, default=func.now())

    @staticmethod
    def generate_client_id() -> str:
        """Generate a unique client ID"""
        return secrets.token_urlsafe(32)


class AuthorizationCode(Base):
    """OAuth authorization codes (short-lived, single use)"""
    __tablename__ = "authorization_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    code_hash = Column(String(64), unique=True, nullable=False)  # SHA256 of code
    client_id = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    redirect_uri = Column(String(500), nullable=True)
    code_challenge = Column(String(128), nullable=True)  # PKCE
    code_challenge_method = Column(String(10), nullable=True)  # S256 or plain
    scope = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    @staticmethod
    def generate_code() -> str:
        """Generate a secure authorization code"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_code(code: str) -> str:
        """Hash authorization code"""
        return hashlib.sha256(code.encode()).hexdigest()

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class OAuthToken(Base):
    """OAuth access tokens"""
    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True)
    access_token_hash = Column(String(64), unique=True, nullable=False, index=True)
    refresh_token_hash = Column(String(64), unique=True, nullable=True, index=True)
    client_id = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scope = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    refresh_expires_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    @staticmethod
    def generate_token() -> str:
        """Generate a secure token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token"""
        return hashlib.sha256(token.encode()).hexdigest()

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    discord_user_id = Column(String(20), unique=True, nullable=False)
    discord_username = Column(String(100), nullable=False)
    api_key_hash = Column(String(64), unique=True, nullable=False)  # PBKDF2-HMAC-SHA256 hash
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
        """Hash an API key using a computationally expensive KDF (PBKDF2-HMAC-SHA256)"""
        # Note: Using a fixed, application-wide salt keeps the hash deterministic
        # so it can be used in equality comparisons in database queries.
        salt = b"discord-mcp-api-key-v1"
        dk = hashlib.pbkdf2_hmac("sha256", api_key.encode(), salt, 200_000, dklen=32)
        return dk.hex()

    @staticmethod
    def hash_api_key_legacy(api_key: str) -> str:
        """Legacy SHA256 hash - used only for migration from old hashes"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def update_usage(self):
        """Update usage statistics"""
        self.last_used = datetime.utcnow()
        self.usage_count += 1