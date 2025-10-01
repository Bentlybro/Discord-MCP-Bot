import discord
import logging
import asyncio
from discord.ext import commands
from discord import app_commands
from typing import List, Optional

from ..config.settings import settings
from ..database.database import db
from ..utils.discord_url_parser import DiscordURLParser

logger = logging.getLogger(__name__)

class DiscordBot:
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.guild_reactions = True
        intents.message_content = True
        # Add member and presence intents for user listing
        intents.members = True
        intents.presences = True

        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self._setup_events()

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            logger.info(f'{self.bot.user} has connected to Discord!')
            logger.info(f'Bot is in {len(self.bot.guilds)} guilds')

            # Initialize database
            await db.init_db()

            # Sync slash commands
            try:
                synced = await self.bot.tree.sync()
                logger.info(f"Synced {len(synced)} slash commands")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")

        # Add slash commands
        @self.bot.tree.command(name="register", description="Register for MCP API access")
        async def register_command(interaction: discord.Interaction):
            await self._handle_register(interaction)

        @self.bot.tree.command(name="regenerate", description="Regenerate your API key")
        async def regenerate_command(interaction: discord.Interaction):
            await self._handle_regenerate(interaction)

        @self.bot.tree.command(name="status", description="Check your account status")
        async def status_command(interaction: discord.Interaction):
            await self._handle_status(interaction)

    def check_channel_access(self, channel_id: int) -> bool:
        """Check if bot has access to a specific channel or thread"""
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return False

        # For threads, check the parent channel permissions
        if isinstance(channel, discord.Thread):
            parent_channel = channel.parent
            if not parent_channel:
                return False

            # If allowed_channels is set, check parent channel
            if settings.allowed_channels:
                return parent_channel.id in settings.allowed_channels

            # If allowed_guilds is set, check guild
            if settings.allowed_guilds:
                return parent_channel.guild.id in settings.allowed_guilds
        else:
            # Regular channel access check
            if settings.allowed_channels:
                return channel_id in settings.allowed_channels

            if settings.allowed_guilds:
                return channel.guild.id in settings.allowed_guilds

        # If neither is set, allow all channels (be careful with this!)
        return True

    async def get_messages(self, channel_id: int, limit: int = 10, before_message_id: Optional[str] = None) -> dict:
        """Get recent messages from a channel"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            messages = []
            before = None
            if before_message_id:
                before = discord.Object(id=int(before_message_id))

            async for message in channel.history(limit=limit, before=before):
                messages.append({
                    "id": str(message.id),
                    "author": message.author.display_name,
                    "author_id": str(message.author.id),
                    "content": message.content,
                    "timestamp": message.created_at.isoformat(),
                    "channel_id": str(message.channel.id),
                    "channel_name": message.channel.name,
                    "guild_id": str(message.guild.id),
                    "guild_name": message.guild.name
                })

            return {"messages": messages}
        except Exception as e:
            return {"error": str(e)}

    async def search_messages(self, channel_id: int, query: str, limit: int = 10) -> dict:
        """Search for messages in a specific channel"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            messages = []
            count = 0

            async for message in channel.history(limit=1000):
                if count >= limit:
                    break

                if query.lower() in message.content.lower():
                    messages.append({
                        "id": str(message.id),
                        "author": message.author.display_name,
                        "author_id": str(message.author.id),
                        "content": message.content,
                        "timestamp": message.created_at.isoformat(),
                        "channel_id": str(message.channel.id),
                        "channel_name": message.channel.name,
                        "guild_id": str(message.guild.id),
                        "guild_name": message.guild.name
                    })
                    count += 1

            return {"messages": messages}
        except Exception as e:
            return {"error": str(e)}

    async def search_guild_messages(self, guild_id: int, query: str, limit: int = 50) -> dict:
        """Search for messages across all channels in a guild"""
        try:
            # Check if we have access to this guild
            if settings.allowed_guilds and guild_id not in settings.allowed_guilds:
                return {"error": "Access denied to this guild"}

            guild = self.bot.get_guild(guild_id)
            if not guild:
                return {"error": "Guild not found"}

            messages = []
            total_found = 0

            # Search through all accessible text channels in the guild
            for channel in guild.text_channels:
                if total_found >= limit:
                    break

                # Check channel access (respects allowed_channels if set)
                if settings.allowed_channels and channel.id not in settings.allowed_channels:
                    continue

                try:
                    # Search in each channel (limit per channel to avoid overwhelming)
                    channel_limit = min(500, limit - total_found)
                    async for message in channel.history(limit=channel_limit):
                        if total_found >= limit:
                            break

                        if query.lower() in message.content.lower():
                            messages.append({
                                "id": str(message.id),
                                "author": message.author.display_name,
                                "author_id": str(message.author.id),
                                "content": message.content,
                                "timestamp": message.created_at.isoformat(),
                                "channel_id": str(message.channel.id),
                                "channel_name": message.channel.name,
                                "guild_id": str(message.guild.id),
                                "guild_name": message.guild.name
                            })
                            total_found += 1

                except discord.Forbidden:
                    # Skip channels we don't have permission to read
                    continue
                except Exception as e:
                    logger.warning(f"Error searching channel {channel.name}: {str(e)}")
                    continue

            return {
                "messages": messages,
                "total_found": total_found,
                "channels_searched": len([ch for ch in guild.text_channels if not settings.allowed_channels or ch.id in settings.allowed_channels]),
                "query": query,
                "guild_name": guild.name
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_message_by_url(self, message_url: str) -> dict:
        """Get a specific message by Discord URL"""
        try:
            # Parse the Discord URL
            parsed = DiscordURLParser.parse_message_url(message_url)
            if not parsed:
                return {"error": "Invalid Discord message URL format"}

            guild_id, channel_id, message_id = parsed

            # Check access to the channel
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            # Get the channel
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            # Fetch the specific message
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                return {"error": "Message not found"}
            except discord.Forbidden:
                return {"error": "No permission to read this message"}

            # Return message data
            message_data = {
                "id": str(message.id),
                "author": message.author.display_name,
                "author_id": str(message.author.id),
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
                "channel_id": str(message.channel.id),
                "channel_name": message.channel.name,
                "guild_id": str(message.guild.id),
                "guild_name": message.guild.name,
                "url": message.jump_url,
                "attachments": [
                    {
                        "filename": att.filename,
                        "url": att.url,
                        "size": att.size
                    } for att in message.attachments
                ],
                "embeds": len(message.embeds),
                "reactions": [
                    {
                        "emoji": str(reaction.emoji),
                        "count": reaction.count
                    } for reaction in message.reactions
                ]
            }

            return {"message": message_data}

        except Exception as e:
            logger.error(f"Error getting message by URL: {str(e)}")
            return {"error": str(e)}

    def list_channels(self) -> dict:
        """List all accessible Discord channels and threads"""
        try:
            channels = []

            for guild in self.bot.guilds:
                # If allowed_guilds is set, only include those guilds
                if settings.allowed_guilds and guild.id not in settings.allowed_guilds:
                    continue

                # Add text channels
                for channel in guild.text_channels:
                    # If allowed_channels is set, only include those specific channels
                    if settings.allowed_channels and channel.id not in settings.allowed_channels:
                        continue

                    channels.append({
                        "id": str(channel.id),
                        "name": channel.name,
                        "type": "text",
                        "guild_id": str(guild.id),
                        "guild_name": guild.name
                    })

                    # Add active threads from this channel
                    try:
                        for thread in channel.threads:
                            # Check if we should include this thread
                            if settings.allowed_channels and channel.id not in settings.allowed_channels:
                                continue

                            channels.append({
                                "id": str(thread.id),
                                "name": f"🧵 {thread.name}",
                                "type": "thread",
                                "parent_id": str(channel.id),
                                "parent_name": channel.name,
                                "guild_id": str(guild.id),
                                "guild_name": guild.name,
                                "archived": thread.archived,
                                "member_count": thread.member_count or 0
                            })
                    except Exception as e:
                        logger.warning(f"Error getting threads for channel {channel.name}: {e}")

            return {"channels": channels}
        except Exception as e:
            return {"error": str(e)}

    async def send_message(self, channel_id: int, content: str, reply_to_message_id: Optional[str] = None, requesting_user_id: Optional[str] = None, is_question: bool = False) -> dict:
        """Send a message to a Discord channel"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            # Check if we have permission to send messages
            if hasattr(channel, 'permissions_for'):
                permissions = channel.permissions_for(channel.guild.me)
                if not permissions.send_messages:
                    return {"error": "Bot doesn't have permission to send messages in this channel"}

            # Handle reply if specified
            reference = None
            if reply_to_message_id:
                try:
                    reference_message = await channel.fetch_message(int(reply_to_message_id))
                    reference = reference_message
                except discord.NotFound:
                    return {"error": "Reply target message not found"}
                except discord.Forbidden:
                    return {"error": "No permission to access reply target message"}

            # Add attribution footer if we have a requesting user
            final_content = content
            if requesting_user_id:
                try:
                    requesting_user = self.bot.get_user(int(requesting_user_id))
                    action = "Asked" if is_question else "Sent"
                    if requesting_user:
                        attribution = f"\n\n*— {action} by {requesting_user.display_name}'s Claude*"
                    else:
                        # Fallback if user not found
                        attribution = f"\n\n*— {action} by <@{requesting_user_id}>'s Claude*"
                    final_content = f"{content}{attribution}"
                except Exception as e:
                    logger.warning(f"Failed to add attribution: {e}")
                    # Continue without attribution if there's an error

            # Send the message
            sent_message = await channel.send(final_content, reference=reference)

            return {
                "success": True,
                "message": {
                    "id": str(sent_message.id),
                    "content": sent_message.content,
                    "timestamp": sent_message.created_at.isoformat(),
                    "channel_id": str(sent_message.channel.id),
                    "channel_name": sent_message.channel.name,
                    "guild_id": str(sent_message.guild.id),
                    "guild_name": sent_message.guild.name,
                    "url": sent_message.jump_url
                }
            }
        except discord.Forbidden:
            return {"error": "Bot doesn't have permission to send messages"}
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return {"error": str(e)}

    async def wait_for_reply(self, channel_id: int, question: str, timeout: int = 300, target_user_id: Optional[str] = None, requesting_user_id: Optional[str] = None) -> dict:
        """Send a question and wait for a reply in a Discord channel"""
        try:
            # First send the question with attribution (mark as question)
            send_result = await self.send_message(channel_id, question, requesting_user_id=requesting_user_id, is_question=True)
            if "error" in send_result:
                return send_result

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            def check(message):
                # Message must be in the same channel
                if message.channel.id != channel_id:
                    return False

                # Message must not be from the bot itself
                if message.author.id == self.bot.user.id:
                    return False

                # If target_user_id specified, only accept messages from that user
                if target_user_id and str(message.author.id) != target_user_id:
                    return False

                return True

            # Wait for response
            try:
                response_message = await self.bot.wait_for('message', check=check, timeout=timeout)

                return {
                    "success": True,
                    "question_message": send_result["message"],
                    "response": {
                        "id": str(response_message.id),
                        "author": response_message.author.display_name,
                        "author_id": str(response_message.author.id),
                        "content": response_message.content,
                        "timestamp": response_message.created_at.isoformat(),
                        "url": response_message.jump_url
                    }
                }
            except asyncio.TimeoutError:
                return {
                    "error": "Timeout waiting for response",
                    "question_message": send_result["message"],
                    "timeout": timeout
                }

        except Exception as e:
            logger.error(f"Error in wait_for_reply: {str(e)}")
            return {"error": str(e)}

    async def list_guild_users(self, guild_id: int, include_bots: bool = False) -> dict:
        """List all users in a Discord guild"""
        try:
            # Check if we have access to this guild
            if settings.allowed_guilds and guild_id not in settings.allowed_guilds:
                return {"error": "Access denied to this guild"}

            guild = self.bot.get_guild(guild_id)
            if not guild:
                return {"error": "Guild not found"}

            # Debug logging
            logger.info(f"Guild {guild.name} - cached members: {len(guild.members)}, total: {guild.member_count}")

            # If we don't have members cached, try to chunk/fetch them
            if len(guild.members) == 0 or len(guild.members) < guild.member_count:
                logger.info("Members not cached, attempting to fetch...")
                try:
                    # This fetches all members for the guild
                    await guild.chunk(cache=True)
                    logger.info(f"After chunking - cached members: {len(guild.members)}")
                except Exception as chunk_error:
                    logger.warning(f"Failed to chunk guild members: {chunk_error}")

            users = []
            for member in guild.members:
                # Skip bots unless explicitly requested
                if member.bot and not include_bots:
                    continue

                # Get user status
                status = "offline"
                if member.status:
                    status = str(member.status)

                users.append({
                    "id": str(member.id),
                    "username": member.name,
                    "display_name": member.display_name,
                    "discriminator": member.discriminator,
                    "is_bot": member.bot,
                    "status": status,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                    "roles": [role.name for role in member.roles if role.name != "@everyone"],
                    "avatar_url": str(member.avatar.url) if member.avatar else None,
                    "mention": member.mention
                })

            logger.info(f"Returning {len(users)} users (include_bots: {include_bots})")

            return {
                "guild_name": guild.name,
                "guild_id": str(guild.id),
                "total_members": guild.member_count,
                "users": users,
                "users_returned": len(users)
            }

        except Exception as e:
            logger.error(f"Error listing guild users: {str(e)}")
            return {"error": str(e)}

    async def list_all_accessible_users(self, include_bots: bool = False) -> dict:
        """List all users across all accessible guilds"""
        try:
            all_users = {}  # Use dict to deduplicate users across guilds
            guild_info = []

            for guild in self.bot.guilds:
                # If allowed_guilds is set, only include those guilds
                if settings.allowed_guilds and guild.id not in settings.allowed_guilds:
                    continue

                guild_users = []
                for member in guild.members:
                    # Skip bots unless explicitly requested
                    if member.bot and not include_bots:
                        continue

                    user_id = str(member.id)

                    # Get user status
                    status = "offline"
                    if member.status:
                        status = str(member.status)

                    user_data = {
                        "id": user_id,
                        "username": member.name,
                        "display_name": member.display_name,
                        "discriminator": member.discriminator,
                        "is_bot": member.bot,
                        "status": status,
                        "avatar_url": str(member.avatar.url) if member.avatar else None,
                        "mention": member.mention
                    }

                    # Add to all_users (deduplicates across guilds)
                    if user_id not in all_users:
                        all_users[user_id] = user_data

                    guild_users.append(user_data)

                guild_info.append({
                    "guild_id": str(guild.id),
                    "guild_name": guild.name,
                    "member_count": len(guild_users),
                    "users": guild_users
                })

            return {
                "unique_users": list(all_users.values()),
                "total_unique_users": len(all_users),
                "guilds": guild_info,
                "total_guilds": len(guild_info)
            }

        except Exception as e:
            logger.error(f"Error listing all users: {str(e)}")
            return {"error": str(e)}

    async def start(self):
        """Start the Discord bot"""
        await self.bot.start(settings.discord_token)

    def is_ready(self) -> bool:
        """Check if bot is ready"""
        return self.bot.is_ready()

    @property
    def guild_count(self) -> int:
        """Get number of guilds bot is in"""
        return len(self.bot.guilds) if self.bot.is_ready() else 0

    async def _handle_register(self, interaction: discord.Interaction):
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

            # Always send as ephemeral (no DM fallback)
            await interaction.response.send_message(instructions, ephemeral=True)

        except Exception as e:
            logger.error(f"Registration error: {e}")
            await interaction.response.send_message(
                "❌ Registration failed. Please try again later.",
                ephemeral=True
            )

    async def _handle_regenerate(self, interaction: discord.Interaction):
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

            # Always send as ephemeral (no DM fallback)
            await interaction.response.send_message(message, ephemeral=True)

        except Exception as e:
            logger.error(f"Regenerate error: {e}")
            await interaction.response.send_message(
                "❌ Failed to regenerate API key.",
                ephemeral=True
            )

    async def _handle_status(self, interaction: discord.Interaction):
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