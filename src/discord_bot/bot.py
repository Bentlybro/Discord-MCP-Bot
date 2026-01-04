"""
Discord Bot core functionality.
Handles Discord API operations for messages, channels, and users.
"""
import discord
import logging
import asyncio
import aiohttp
import base64
from discord.ext import commands
from typing import Optional

from ..config.settings import settings
from ..database.database import db
from ..utils.discord_url_parser import DiscordURLParser
from .formatters import format_message, format_message_full, format_user, format_channel, format_thread
from .commands import setup_commands
from .access import AccessChecker

logger = logging.getLogger(__name__)


class DiscordBot:
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.guild_reactions = True
        intents.members = True
        intents.presences = True

        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.access = AccessChecker(self.bot)
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

        # Setup slash commands from commands module
        setup_commands(self.bot)

    # Channel access delegation
    def check_channel_access(self, channel_id: int) -> bool:
        return self.access.check_channel_access(channel_id)

    def check_guild_access(self, guild_id: int) -> bool:
        return self.access.check_guild_access(guild_id)

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
                messages.append(format_message(message))

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
                    messages.append(format_message(message))
                    count += 1

            return {"messages": messages}
        except Exception as e:
            return {"error": str(e)}

    async def search_guild_messages(self, guild_id: int, query: str, limit: int = 50) -> dict:
        """Search for messages across all channels in a guild"""
        try:
            if not self.check_guild_access(guild_id):
                return {"error": "Access denied to this guild"}

            guild = self.bot.get_guild(guild_id)
            if not guild:
                return {"error": "Guild not found"}

            messages = []
            total_found = 0
            channels_searched = 0

            for channel in guild.text_channels:
                if total_found >= limit:
                    break

                # Check channel access (respects allowed_channels if set)
                if not self.access.is_channel_allowed(channel):
                    continue

                # Check if bot can actually read this channel
                if not self.access.can_read_channel(channel):
                    continue

                channels_searched += 1

                try:
                    channel_limit = min(500, limit - total_found)
                    async for message in channel.history(limit=channel_limit):
                        if total_found >= limit:
                            break

                        if query.lower() in message.content.lower():
                            messages.append(format_message(message))
                            total_found += 1

                except discord.Forbidden:
                    continue
                except Exception as e:
                    logger.warning(f"Error searching channel {channel.name}: {str(e)}")
                    continue

            return {
                "messages": messages,
                "total_found": total_found,
                "channels_searched": channels_searched,
                "query": query,
                "guild_name": guild.name
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_message_by_url(self, message_url: str) -> dict:
        """Get a specific message by Discord URL"""
        try:
            parsed = DiscordURLParser.parse_message_url(message_url)
            if not parsed:
                return {"error": "Invalid Discord message URL format"}

            guild_id, channel_id, message_id = parsed

            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                return {"error": "Message not found"}
            except discord.Forbidden:
                return {"error": "No permission to read this message"}

            return {"message": format_message_full(message)}

        except Exception as e:
            logger.error(f"Error getting message by URL: {str(e)}")
            return {"error": str(e)}

    def list_channels(self) -> dict:
        """List all accessible Discord channels and threads"""
        try:
            channels = []

            for guild in self.bot.guilds:
                if settings.allowed_guilds and guild.id not in settings.allowed_guilds:
                    continue

                for channel in guild.text_channels:
                    # Check config-based access
                    if not self.access.is_channel_allowed(channel):
                        continue

                    # Check if bot can actually read this channel
                    if not self.access.can_read_channel(channel):
                        continue

                    channels.append(format_channel(channel))

                    # Add active threads from this channel
                    try:
                        for thread in channel.threads:
                            channels.append(format_thread(thread))
                    except Exception as e:
                        logger.warning(f"Error getting threads for channel {channel.name}: {e}")

            return {"channels": channels}
        except Exception as e:
            return {"error": str(e)}

    def get_channel_info(self, channel_id: int) -> dict:
        """Get detailed information about a channel"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            # Base info for all channel types
            info = {
                "id": str(channel.id),
                "name": channel.name,
                "guild_id": str(channel.guild.id),
                "guild_name": channel.guild.name,
                "created_at": channel.created_at.isoformat() if channel.created_at else None,
            }

            # Thread-specific info
            if isinstance(channel, discord.Thread):
                info["type"] = "thread"
                info["parent_id"] = str(channel.parent_id)
                info["parent_name"] = channel.parent.name if channel.parent else None
                info["owner_id"] = str(channel.owner_id) if channel.owner_id else None
                info["message_count"] = channel.message_count
                info["member_count"] = channel.member_count
                info["archived"] = channel.archived
                info["locked"] = channel.locked
                info["auto_archive_duration"] = channel.auto_archive_duration
            else:
                # Text channel info
                info["type"] = "text"
                info["topic"] = channel.topic
                info["category"] = channel.category.name if channel.category else None
                info["category_id"] = str(channel.category_id) if channel.category_id else None
                info["position"] = channel.position
                info["slowmode_delay"] = channel.slowmode_delay
                info["nsfw"] = channel.nsfw
                info["is_news"] = channel.is_news()

                # Thread count if available
                info["thread_count"] = len(channel.threads)

            return {"channel": info}
        except Exception as e:
            return {"error": str(e)}

    async def send_message(self, channel_id: int, content: str, reply_to_message_id: Optional[str] = None,
                          requesting_user_id: Optional[str] = None, is_question: bool = False) -> dict:
        """Send a message to a Discord channel"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            if not self.access.can_send_to_channel(channel):
                return {"error": "Bot doesn't have permission to send messages in this channel"}

            # Handle reply if specified
            reference = None
            if reply_to_message_id:
                try:
                    reference = await channel.fetch_message(int(reply_to_message_id))
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
                        attribution = f"\n\n*— {action} by <@{requesting_user_id}>'s Claude*"
                    final_content = f"{content}{attribution}"
                except Exception as e:
                    logger.warning(f"Failed to add attribution: {e}")

            sent_message = await channel.send(final_content, reference=reference)

            return {
                "success": True,
                "message": format_message(sent_message)
            }
        except discord.Forbidden:
            return {"error": "Bot doesn't have permission to send messages"}
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return {"error": str(e)}

    async def wait_for_reply(self, channel_id: int, question: str, timeout: int = 300,
                            target_user_id: Optional[str] = None, requesting_user_id: Optional[str] = None) -> dict:
        """Send a question and wait for a reply in a Discord channel"""
        try:
            # First send the question with attribution
            send_result = await self.send_message(channel_id, question, requesting_user_id=requesting_user_id, is_question=True)
            if "error" in send_result:
                return send_result

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            def check(message):
                if message.channel.id != channel_id:
                    return False
                if message.author.id == self.bot.user.id:
                    return False
                if target_user_id and str(message.author.id) != target_user_id:
                    return False
                return True

            try:
                response_message = await self.bot.wait_for('message', check=check, timeout=timeout)

                return {
                    "success": True,
                    "question_message": send_result["message"],
                    "response": format_message(response_message)
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
            if not self.check_guild_access(guild_id):
                return {"error": "Access denied to this guild"}

            guild = self.bot.get_guild(guild_id)
            if not guild:
                return {"error": "Guild not found"}

            # Fetch members if not cached
            if len(guild.members) < guild.member_count:
                try:
                    await guild.chunk(cache=True)
                except Exception as e:
                    logger.warning(f"Failed to chunk guild members: {e}")

            users = []
            for member in guild.members:
                if member.bot and not include_bots:
                    continue
                users.append(format_user(member, include_roles=True))

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
            all_users = {}  # Deduplicate across guilds
            guild_info = []

            for guild in self.bot.guilds:
                if settings.allowed_guilds and guild.id not in settings.allowed_guilds:
                    continue

                guild_users = []
                for member in guild.members:
                    if member.bot and not include_bots:
                        continue

                    user_data = format_user(member)
                    user_id = user_data["id"]

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

    async def get_pinned_messages(self, channel_id: int) -> dict:
        """Get all pinned messages from a channel"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            pinned = await channel.pins()
            messages = [format_message_full(msg) for msg in pinned]

            return {
                "channel_id": str(channel_id),
                "channel_name": channel.name,
                "pinned_count": len(messages),
                "messages": messages
            }
        except Exception as e:
            logger.error(f"Error getting pinned messages: {str(e)}")
            return {"error": str(e)}

    async def get_message_context(self, channel_id: int, message_id: str,
                                  before_count: int = 5, after_count: int = 5) -> dict:
        """Get messages before and after a specific message for context"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            # Fetch the target message
            try:
                target_message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                return {"error": "Message not found"}

            # Get messages before
            before_messages = []
            async for msg in channel.history(limit=before_count, before=target_message):
                before_messages.append(format_message(msg))
            before_messages.reverse()  # Chronological order

            # Get messages after
            after_messages = []
            async for msg in channel.history(limit=after_count, after=target_message):
                after_messages.append(format_message(msg))
            after_messages.reverse()  # Chronological order

            return {
                "before": before_messages,
                "target": format_message_full(target_message),
                "after": after_messages,
                "channel_id": str(channel_id),
                "channel_name": channel.name
            }
        except Exception as e:
            logger.error(f"Error getting message context: {str(e)}")
            return {"error": str(e)}

    async def get_message_by_id(self, channel_id: int, message_id: str) -> dict:
        """Get a specific message by its ID"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                return {"error": "Message not found"}
            except discord.Forbidden:
                return {"error": "No permission to read this message"}

            return {"message": format_message_full(message)}

        except Exception as e:
            logger.error(f"Error getting message by ID: {str(e)}")
            return {"error": str(e)}

    async def trace_reply_chain(self, channel_id: int, message_id: str, max_depth: int = 20) -> dict:
        """Trace back through a chain of message replies"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            # Clamp max_depth
            max_depth = min(max(1, max_depth), 50)

            chain = []
            current_message_id = int(message_id)

            for _ in range(max_depth):
                try:
                    message = await channel.fetch_message(current_message_id)
                except discord.NotFound:
                    # If we can't find a message in the chain, stop here
                    if not chain:
                        return {"error": "Message not found"}
                    break
                except discord.Forbidden:
                    if not chain:
                        return {"error": "No permission to read this message"}
                    break

                # Add to chain
                chain.append(format_message_full(message))

                # Check if this message is a reply
                if message.reference and message.reference.message_id:
                    current_message_id = message.reference.message_id
                else:
                    # No more replies to trace
                    break

            # Reverse so oldest message is first (chronological order)
            chain.reverse()

            return {
                "chain": chain,
                "message_count": len(chain),
                "channel_id": str(channel_id),
                "channel_name": channel.name,
                "complete": len(chain) < max_depth or not (chain and chain[-1].get("reply_to_message_id"))
            }

        except Exception as e:
            logger.error(f"Error tracing reply chain: {str(e)}")
            return {"error": str(e)}

    async def edit_message(self, channel_id: int, message_id: str, new_content: str) -> dict:
        """Edit a message that the bot previously sent"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                return {"error": "Message not found"}

            # Check if the message was sent by the bot
            if message.author.id != self.bot.user.id:
                return {"error": "Can only edit messages sent by this bot"}

            edited_message = await message.edit(content=new_content)

            return {
                "success": True,
                "message": format_message(edited_message)
            }
        except discord.Forbidden:
            return {"error": "No permission to edit this message"}
        except Exception as e:
            logger.error(f"Error editing message: {str(e)}")
            return {"error": str(e)}

    async def delete_message(self, channel_id: int, message_id: str) -> dict:
        """Delete a message that the bot previously sent"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                return {"error": "Message not found"}

            # Check if the message was sent by the bot
            if message.author.id != self.bot.user.id:
                return {"error": "Can only delete messages sent by this bot"}

            await message.delete()

            return {
                "success": True,
                "deleted_message_id": message_id
            }
        except discord.Forbidden:
            return {"error": "No permission to delete this message"}
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
            return {"error": str(e)}

    async def create_thread(self, channel_id: int, name: str, message_id: Optional[str] = None,
                           auto_archive_duration: int = 1440) -> dict:
        """Create a new thread from a message or as a standalone thread"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            # Validate auto_archive_duration
            valid_durations = [60, 1440, 4320, 10080]
            if auto_archive_duration not in valid_durations:
                auto_archive_duration = 1440  # Default to 24 hours

            if message_id:
                # Create thread from a message
                try:
                    message = await channel.fetch_message(int(message_id))
                    thread = await message.create_thread(
                        name=name,
                        auto_archive_duration=auto_archive_duration
                    )
                except discord.NotFound:
                    return {"error": "Message not found"}
            else:
                # Create standalone thread
                thread = await channel.create_thread(
                    name=name,
                    auto_archive_duration=auto_archive_duration,
                    type=discord.ChannelType.public_thread
                )

            return {
                "success": True,
                "thread": format_thread(thread)
            }
        except discord.Forbidden:
            return {"error": "No permission to create threads in this channel"}
        except Exception as e:
            logger.error(f"Error creating thread: {str(e)}")
            return {"error": str(e)}

    async def dm_user(self, user_id: str, content: str, requesting_user_id: Optional[str] = None) -> dict:
        """Send a direct message to a user"""
        try:
            user = self.bot.get_user(int(user_id))
            if not user:
                # Try to fetch the user if not in cache
                try:
                    user = await self.bot.fetch_user(int(user_id))
                except discord.NotFound:
                    return {"error": "User not found"}

            # Add attribution if we have a requesting user
            final_content = content
            if requesting_user_id:
                try:
                    requesting_user = self.bot.get_user(int(requesting_user_id))
                    if requesting_user:
                        attribution = f"\n\n*— Sent by {requesting_user.display_name}'s Claude*"
                    else:
                        attribution = f"\n\n*— Sent by <@{requesting_user_id}>'s Claude*"
                    final_content = f"{content}{attribution}"
                except Exception as e:
                    logger.warning(f"Failed to add attribution: {e}")

            # Create DM channel and send
            dm_channel = await user.create_dm()
            sent_message = await dm_channel.send(final_content)

            return {
                "success": True,
                "message": {
                    "id": str(sent_message.id),
                    "content": sent_message.content,
                    "timestamp": sent_message.created_at.isoformat(),
                    "recipient": {
                        "id": str(user.id),
                        "username": user.name,
                        "display_name": user.display_name
                    }
                }
            }
        except discord.Forbidden:
            return {"error": "Cannot send DM to this user (they may have DMs disabled)"}
        except Exception as e:
            logger.error(f"Error sending DM: {str(e)}")
            return {"error": str(e)}

    async def download_attachment(self, channel_id: int, message_id: str,
                                  attachment_index: int = 0) -> dict:
        """Download an attachment from a message"""
        try:
            if not self.check_channel_access(channel_id):
                return {"error": "Access denied to this channel"}

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"error": "Channel not found"}

            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                return {"error": "Message not found"}

            if not message.attachments:
                return {"error": "Message has no attachments"}

            if attachment_index >= len(message.attachments):
                return {"error": f"Attachment index {attachment_index} out of range (message has {len(message.attachments)} attachments)"}

            attachment = message.attachments[attachment_index]

            # Check file size (limit to 10MB to avoid memory issues)
            if attachment.size > 10 * 1024 * 1024:
                return {"error": "Attachment too large (max 10MB)"}

            # Download the attachment
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as response:
                    if response.status != 200:
                        return {"error": f"Failed to download attachment: HTTP {response.status}"}

                    content = await response.read()

            # Determine if it's text or binary
            is_text = attachment.content_type and attachment.content_type.startswith(('text/', 'application/json', 'application/xml'))

            if is_text:
                try:
                    text_content = content.decode('utf-8')
                    return {
                        "success": True,
                        "filename": attachment.filename,
                        "content_type": attachment.content_type,
                        "size": attachment.size,
                        "is_text": True,
                        "content": text_content
                    }
                except UnicodeDecodeError:
                    is_text = False

            # For binary files, return base64 encoded
            return {
                "success": True,
                "filename": attachment.filename,
                "content_type": attachment.content_type,
                "size": attachment.size,
                "is_text": False,
                "content_base64": base64.b64encode(content).decode('ascii')
            }

        except Exception as e:
            logger.error(f"Error downloading attachment: {str(e)}")
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
