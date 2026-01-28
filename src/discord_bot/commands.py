"""
Discord slash command handlers.
Handles user registration, API key management, and status commands.
"""
import discord
import logging
from discord.ext import commands

from ..config.settings import settings
from ..database.database import db

logger = logging.getLogger(__name__)


def setup_commands(bot: commands.Bot):
    """Register all slash commands on the bot"""

    @bot.tree.command(name="register", description="Register for MCP API access")
    async def register_command(interaction: discord.Interaction):
        await handle_register(interaction)

    @bot.tree.command(name="apikey", description="Get or regenerate your API key")
    async def apikey_command(interaction: discord.Interaction):
        await handle_apikey(interaction)

    @bot.tree.command(name="status", description="Check your account status")
    async def status_command(interaction: discord.Interaction):
        await handle_status(interaction)

    @bot.tree.command(name="users", description="List all registered users (admin only)")
    async def users_command(interaction: discord.Interaction):
        await handle_users(interaction)


async def handle_register(interaction: discord.Interaction):
    """Handle /register command"""
    try:
        user_id = str(interaction.user.id)
        username = str(interaction.user)

        # Check if user already exists
        existing_user = await db.get_user_by_discord_id(user_id)
        if existing_user:
            server_url = settings.public_domain
            await interaction.response.send_message(
                f"""✅ **You're already registered!**

**To connect with Claude Code or Claude Desktop:**
```bash
claude mcp add --transport http discord-mcp-bot {server_url}/mcp
```
Then select "Authenticate" when prompted - you'll log in with Discord.

Use `/apikey` if you need an API key for manual authentication.""",
                ephemeral=True
            )
            return

        # Create new user (returns tuple of user and plaintext key)
        user, plaintext_api_key = await db.create_user(user_id, username)

        # Create connection instructions
        server_url = settings.public_domain

        instructions = f"""🎉 **Registration Successful!**

**To connect with Claude Code:**
```bash
claude mcp add --transport http discord-mcp-bot {server_url}/mcp
```
Then select **"Authenticate"** - you'll log in with Discord automatically!

**To connect with Claude Desktop:**
Settings → Connectors → Add custom connector → `{server_url}/mcp`

---
**Backup method (if OAuth doesn't work):**
||`{plaintext_api_key}`||
```bash
claude mcp add --transport http discord-mcp-bot {server_url}/mcp --header "Authorization: Bearer {plaintext_api_key}"
```
*Save this now - you won't see it again! Use `/apikey` to generate a new one.*"""

        await interaction.response.send_message(instructions, ephemeral=True)

    except Exception as e:
        logger.error(f"Registration error: {e}")
        await interaction.response.send_message(
            "❌ Registration failed. Please try again later.",
            ephemeral=True
        )


async def handle_apikey(interaction: discord.Interaction):
    """Handle /apikey command - generate or regenerate API key"""
    try:
        user_id = str(interaction.user.id)
        server_url = settings.public_domain

        # Check if user exists
        existing_user = await db.get_user_by_discord_id(user_id)
        if not existing_user:
            await interaction.response.send_message(
                "❌ You're not registered yet. Use `/register` first.",
                ephemeral=True
            )
            return

        # Regenerate their key
        new_key = await db.regenerate_api_key(user_id)

        message = f"""🔑 **API Key Generated!**

**Your API Key:** ||`{new_key}`||
⚠️ Save this now - you won't see it again!

**When to use this:**
API keys are a backup for when OAuth doesn't work. The recommended way is:
```bash
claude mcp add --transport http discord-mcp-bot {server_url}/mcp
```
Then authenticate with Discord when prompted.

**If you need the API key method:**
```bash
claude mcp add --transport http discord-mcp-bot {server_url}/mcp --header "Authorization: Bearer {new_key}"
```

*Note: Any previous API key is now invalid.*"""

        await interaction.response.send_message(message, ephemeral=True)

    except Exception as e:
        logger.error(f"API key error: {e}")
        await interaction.response.send_message(
            "❌ Failed to generate API key.",
            ephemeral=True
        )


async def handle_status(interaction: discord.Interaction):
    """Handle /status command"""
    try:
        user = await db.get_user_by_discord_id(str(interaction.user.id))
        if not user:
            await interaction.response.send_message(
                "❌ You're not registered yet. Use `/register` first.",
                ephemeral=True
            )
            return

        status_emoji = "✅" if user.is_active else "❌"
        last_used = user.last_used.strftime("%Y-%m-%d %H:%M UTC") if user.last_used else "Never"

        server_url = settings.public_domain
        status_msg = f"""📊 **Account Status**

**Status:** {status_emoji} {"Active" if user.is_active else "Inactive"}
**Username:** {user.discord_username}
**Created:** {user.created_at.strftime("%Y-%m-%d %H:%M UTC")}
**Last Used:** {last_used}
**Usage Count:** {user.usage_count} requests

**Connect to Claude:**
```bash
claude mcp add --transport http discord-mcp-bot {server_url}/mcp
```

**Commands:**
• `/apikey` - Get an API key (backup auth method)
• `/status` - View this status"""

        await interaction.response.send_message(status_msg, ephemeral=True)

    except Exception as e:
        logger.error(f"Status error: {e}")
        await interaction.response.send_message(
            "❌ Failed to get status.",
            ephemeral=True
        )


async def handle_users(interaction: discord.Interaction):
    """Handle /users command - admin only"""
    try:
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ This command is only available to administrators.",
                ephemeral=True
            )
            return

        # Get all users from database
        users = await db.get_all_users()

        if not users:
            await interaction.response.send_message(
                "No registered users found.",
                ephemeral=True
            )
            return

        # Build user list message
        user_lines = []
        total_requests = 0
        active_count = 0

        for user in users:
            status_emoji = "✅" if user.is_active else "❌"
            last_used = user.last_used.strftime("%Y-%m-%d") if user.last_used else "Never"
            user_lines.append(
                f"{status_emoji} **{user.discord_username}** (ID: {user.discord_user_id})\n"
                f"   Created: {user.created_at.strftime('%Y-%m-%d')} | Last Used: {last_used} | Requests: {user.usage_count}"
            )
            total_requests += user.usage_count
            if user.is_active:
                active_count += 1

        # Split into chunks if too long (Discord limit is 2000 chars)
        message = f"""👥 **Registered Users** ({len(users)} total, {active_count} active)

{chr(10).join(user_lines[:20])}

**Total API Requests:** {total_requests}"""

        if len(users) > 20:
            message += f"\n\n*Showing first 20 of {len(users)} users*"

        await interaction.response.send_message(message, ephemeral=True)

    except Exception as e:
        logger.error(f"Users command error: {e}")
        await interaction.response.send_message(
            "❌ Failed to retrieve user list.",
            ephemeral=True
        )
