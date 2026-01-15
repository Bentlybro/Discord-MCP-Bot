"""
OAuth 2.0 endpoints for MCP authentication.
Implements RFC 8414, RFC 9728, and OAuth 2.1 with PKCE.
"""
import hashlib
import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode
from pathlib import Path
import secrets

from fastapi import APIRouter, Request, Response, Form, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import httpx

from ..config.settings import settings
from ..database.database import db
from ..database.models import OAuthClient, AuthorizationCode, OAuthToken

logger = logging.getLogger(__name__)

router = APIRouter()

# Setup Jinja2 templates
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_base_url() -> str:
    """Get the base URL for OAuth endpoints"""
    return settings.public_domain.rstrip('/')


# ============================================================================
# Well-Known Endpoints (RFC 8414, RFC 9728)
# ============================================================================

@router.get("/.well-known/oauth-protected-resource")
async def protected_resource_metadata():
    """
    OAuth 2.0 Protected Resource Metadata (RFC 9728)
    Tells clients where to find the authorization server.
    """
    base_url = get_base_url()
    return {
        "resource": base_url,
        "authorization_servers": [base_url],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{base_url}/docs"
    }


@router.get("/.well-known/oauth-authorization-server")
async def authorization_server_metadata():
    """
    OAuth 2.0 Authorization Server Metadata (RFC 8414)
    Provides all OAuth endpoints and capabilities.
    """
    base_url = get_base_url()
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/authorize",
        "token_endpoint": f"{base_url}/token",
        "registration_endpoint": f"{base_url}/register",
        "revocation_endpoint": f"{base_url}/revoke",
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "service_documentation": f"{base_url}/docs",
        "scopes_supported": ["mcp:tools", "mcp:read", "mcp:write"]
    }


# ============================================================================
# Dynamic Client Registration (RFC 7591)
# ============================================================================

@router.post("/register")
async def register_client(request: Request):
    """
    Dynamic Client Registration endpoint.
    Allows Claude Code/Desktop to register as OAuth clients.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    client_name = body.get("client_name", "Unknown Client")
    redirect_uris = body.get("redirect_uris", [])

    # Generate client credentials
    client_id = OAuthClient.generate_client_id()

    # Store client in database
    await db.create_oauth_client(client_id, client_name, redirect_uris)

    return {
        "client_id": client_id,
        "client_name": client_name,
        "redirect_uris": redirect_uris,
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"]
    }


# ============================================================================
# Authorization Endpoint
# ============================================================================

@router.get("/authorize")
async def authorize(
    request: Request,
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None),
):
    """
    OAuth 2.0 Authorization Endpoint.
    Redirects user to Discord for authentication or shows login page.
    """
    base_url = get_base_url()

    if response_type != "code":
        return JSONResponse(
            {"error": "unsupported_response_type"},
            status_code=400
        )

    # Validate PKCE
    if code_challenge and code_challenge_method not in ["S256", "plain"]:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Invalid code_challenge_method"},
            status_code=400
        )

    # If Discord OAuth is configured, redirect to Discord
    if settings.discord_client_id and settings.discord_client_secret:
        auth_state = secrets.token_urlsafe(32)
        await db.store_pending_auth(
            auth_state=auth_state,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            original_state=state
        )

        discord_auth_url = "https://discord.com/api/oauth2/authorize"
        params = {
            "client_id": settings.discord_client_id,
            "redirect_uri": f"{base_url}/callback",
            "response_type": "code",
            "scope": "identify",
            "state": auth_state
        }
        return RedirectResponse(url=f"{discord_auth_url}?{urlencode(params)}")

    # Fallback: Show login page for API key authentication
    return templates.TemplateResponse("login.html", {
        "request": request,
        "client_id": client_id or "",
        "redirect_uri": redirect_uri or "",
        "state": state or "",
        "scope": scope or "",
        "code_challenge": code_challenge or "",
        "code_challenge_method": code_challenge_method or "",
        "error": None
    })


@router.post("/authorize")
async def authorize_submit(
    request: Request,
    api_key: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(None),
    state: str = Form(None),
    scope: str = Form(None),
    code_challenge: str = Form(None),
    code_challenge_method: str = Form(None),
):
    """
    Handle API key login form submission.
    Validates the user's existing API key and issues an auth code.
    """
    user = await db.get_user_by_api_key(api_key)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "client_id": client_id or "",
            "redirect_uri": redirect_uri or "",
            "state": state or "",
            "scope": scope or "",
            "code_challenge": code_challenge or "",
            "code_challenge_method": code_challenge_method or "",
            "error": "Invalid API key. Get your API key from the Discord bot with /apikey"
        }, status_code=401)

    # Generate authorization code
    code = AuthorizationCode.generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.oauth_code_expiry_minutes)

    await db.create_authorization_code(
        code=code,
        client_id=client_id,
        user_id=user.id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        scope=scope,
        expires_at=expires_at
    )

    # Redirect back to client with code
    if redirect_uri:
        params = {"code": code}
        if state:
            params["state"] = state
        separator = "&" if "?" in redirect_uri else "?"
        return RedirectResponse(url=f"{redirect_uri}{separator}{urlencode(params)}")

    # If no redirect_uri, show the code
    return templates.TemplateResponse("success.html", {
        "request": request,
        "code": code,
        "username": None
    })


@router.get("/callback")
async def discord_callback(
    request: Request,
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
):
    """
    Discord OAuth callback handler.
    Exchanges Discord code for user info, then issues MCP auth code.
    """
    if error:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "Authorization Failed",
            "message": error
        }, status_code=400)

    if not code or not state:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "Invalid Request",
            "message": "Missing code or state parameter"
        }, status_code=400)

    pending = await db.get_pending_auth(state)
    if not pending:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "Session Expired",
            "message": "Please try again"
        }, status_code=400)

    base_url = get_base_url()

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{base_url}/callback"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if token_response.status_code != 200:
            logger.error(f"Discord token exchange failed: {token_response.text}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "title": "Discord Authorization Failed",
                "message": "Failed to exchange code for token"
            }, status_code=400)

        token_data = token_response.json()
        access_token = token_data["access_token"]

        user_response = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if user_response.status_code != 200:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "title": "Discord Error",
                "message": "Failed to get Discord user info"
            }, status_code=400)

        discord_user = user_response.json()
        discord_user_id = discord_user["id"]
        discord_username = discord_user["username"]

    # Find or create user
    user = await db.get_user_by_discord_id(discord_user_id)
    if not user:
        user, _ = await db.create_user(discord_user_id, discord_username)

    # Generate MCP authorization code
    auth_code = AuthorizationCode.generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.oauth_code_expiry_minutes)

    await db.create_authorization_code(
        code=auth_code,
        client_id=pending["client_id"],
        user_id=user.id,
        redirect_uri=pending["redirect_uri"],
        code_challenge=pending["code_challenge"],
        code_challenge_method=pending["code_challenge_method"],
        scope=pending["scope"],
        expires_at=expires_at
    )

    await db.delete_pending_auth(state)

    redirect_uri = pending["redirect_uri"]
    if redirect_uri:
        params = {"code": auth_code}
        if pending["original_state"]:
            params["state"] = pending["original_state"]
        separator = "&" if "?" in redirect_uri else "?"
        return RedirectResponse(url=f"{redirect_uri}{separator}{urlencode(params)}")

    return templates.TemplateResponse("success.html", {
        "request": request,
        "code": auth_code,
        "username": discord_username
    })


# ============================================================================
# Token Endpoint
# ============================================================================

@router.post("/token")
async def token_endpoint(
    grant_type: str = Form(...),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    client_id: str = Form(None),
    code_verifier: str = Form(None),
    refresh_token: str = Form(None),
):
    """
    OAuth 2.0 Token Endpoint.
    Exchanges authorization code for access token.
    """
    if grant_type == "authorization_code":
        return await handle_authorization_code_grant(
            code=code,
            code_verifier=code_verifier
        )
    elif grant_type == "refresh_token":
        return await handle_refresh_token_grant(refresh_token=refresh_token)
    else:
        return JSONResponse(
            {"error": "unsupported_grant_type"},
            status_code=400
        )


async def handle_authorization_code_grant(
    code: Optional[str],
    code_verifier: Optional[str]
):
    """Exchange authorization code for tokens"""
    if not code:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Missing code"},
            status_code=400
        )

    auth_code = await db.get_authorization_code(code)
    if not auth_code:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Invalid authorization code"},
            status_code=400
        )

    if auth_code.used:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Authorization code already used"},
            status_code=400
        )

    if auth_code.is_expired():
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Authorization code expired"},
            status_code=400
        )

    # Validate PKCE
    if auth_code.code_challenge:
        if not code_verifier:
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Missing code_verifier"},
                status_code=400
            )

        if auth_code.code_challenge_method == "S256":
            challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).rstrip(b"=").decode()
        else:
            challenge = code_verifier

        if challenge != auth_code.code_challenge:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Invalid code_verifier"},
                status_code=400
            )

    await db.mark_authorization_code_used(code)

    access_token = OAuthToken.generate_token()
    refresh_token = OAuthToken.generate_token()

    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.oauth_token_expiry_hours)
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.oauth_refresh_token_expiry_days)

    await db.create_oauth_token(
        access_token=access_token,
        refresh_token=refresh_token,
        client_id=auth_code.client_id,
        user_id=auth_code.user_id,
        scope=auth_code.scope,
        expires_at=expires_at,
        refresh_expires_at=refresh_expires_at
    )

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": settings.oauth_token_expiry_hours * 3600,
        "refresh_token": refresh_token,
        "scope": auth_code.scope or "mcp:tools"
    }


async def handle_refresh_token_grant(refresh_token: Optional[str]):
    """Exchange refresh token for new access token"""
    if not refresh_token:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Missing refresh_token"},
            status_code=400
        )

    token_record = await db.get_token_by_refresh_token(refresh_token)
    if not token_record or token_record.revoked:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Invalid refresh token"},
            status_code=400
        )

    # Make naive datetime timezone-aware for comparison (assume stored as UTC)
    refresh_expires = token_record.refresh_expires_at
    if refresh_expires and refresh_expires.tzinfo is None:
        refresh_expires = refresh_expires.replace(tzinfo=timezone.utc)
    if refresh_expires and datetime.now(timezone.utc) > refresh_expires:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Refresh token expired"},
            status_code=400
        )

    await db.revoke_token(token_record.id)

    new_access_token = OAuthToken.generate_token()
    new_refresh_token = OAuthToken.generate_token()

    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.oauth_token_expiry_hours)
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.oauth_refresh_token_expiry_days)

    await db.create_oauth_token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        client_id=token_record.client_id,
        user_id=token_record.user_id,
        scope=token_record.scope,
        expires_at=expires_at,
        refresh_expires_at=refresh_expires_at
    )

    return {
        "access_token": new_access_token,
        "token_type": "Bearer",
        "expires_in": settings.oauth_token_expiry_hours * 3600,
        "refresh_token": new_refresh_token,
        "scope": token_record.scope or "mcp:tools"
    }


# ============================================================================
# Token Revocation
# ============================================================================

@router.post("/revoke")
async def revoke_token(
    token: str = Form(...),
    token_type_hint: str = Form(None)
):
    """OAuth 2.0 Token Revocation endpoint."""
    await db.revoke_token_by_value(token)
    return Response(status_code=200)
