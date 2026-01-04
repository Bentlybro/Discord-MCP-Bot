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

    @bot.tree.command(name="regenerate", description="Regenerate your API key")
    async def regenerate_command(interaction: discord.Interaction):
        await handle_regenerate(interaction)

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
            await interaction.response.send_message(
                "✅ You're already registered! If you lost your API key, use `/regenerate` to create a new one.",
                ephemeral=True
            )
            return

        # Create new user (returns tuple of user and plaintext key)
        user, plaintext_api_key = await db.create_user(user_id, username)

        # Create connection instructions
        server_url = settings.public_domain

        instructions = f"""🎉 **Registration Successful!**

**Your API Key:** ||`{plaintext_api_key}`||
⚠️ **SAVE THIS NOW! You won't be able to see it again.**

**To connect with Claude Code:**
```bash
claude mcp add --transport http discord-mcp-bot {server_url}/mcp --header "Authorization: Bearer {plaintext_api_key}"
```

**Available Commands:**
• `/regenerate` - Generate a new API key (if you lose this one)
• `/status` - Check your account status and usage"""

        await interaction.response.send_message(instructions, ephemeral=True)

    except Exception as e:
        logger.error(f"Registration error: {e}")
        await interaction.response.send_message(
            "❌ Registration failed. Please try again later.",
            ephemeral=True
        )


async def handle_regenerate(interaction: discord.Interaction):
    """Handle /regenerate command"""
    try:
        new_key = await db.regenerate_api_key(str(interaction.user.id))
        if not new_key:
            await interaction.response.send_message(
                "❌ You're not registered yet. Use `/register` first.",
                ephemeral=True
            )
            return

        server_url = settings.public_domain

        message = f"""🔄 **New API Key Generated!**

**Your New API Key:** ||`{new_key}`||
⚠️ **SAVE THIS NOW! You won't be able to see it again.**

**Your old key is now INVALID!**

**Updated Connection Command:**
```bash
claude mcp remove discord-mcp-bot
claude mcp add --transport http discord-mcp-bot {server_url}/mcp --header "Authorization: Bearer {new_key}"
```

**Important:**
• This is your ONLY chance to copy this key
• Update your Claude Code configuration immediately
• The old key will no longer work"""

        await interaction.response.send_message(message, ephemeral=True)

    except Exception as e:
        logger.error(f"Regenerate error: {e}")
        await interaction.response.send_message(
            "❌ Failed to regenerate API key.",
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

        status_msg = f"""📊 **Account Status**

**Status:** {status_emoji} {"Active" if user.is_active else "Inactive"}
**Username:** {user.discord_username}
**Created:** {user.created_at.strftime("%Y-%m-%d %H:%M UTC")}
**Last Used:** {last_used}
**Usage Count:** {user.usage_count} requests

**Available Commands:**
• `/regenerate` - Generate new API key (invalidates old one)
• `/status` - View this status information

**Note:** API keys are only shown once when created/regenerated for security."""

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
