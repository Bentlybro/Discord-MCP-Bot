"""
Formatting utilities for Discord objects.
Provides consistent dictionary representations for messages and users.
"""
import discord


def format_message(message: discord.Message) -> dict:
    """Format a Discord message into a consistent dictionary structure"""
    data = {
        "id": str(message.id),
        "author": message.author.display_name,
        "author_id": str(message.author.id),
        "content": message.content,
        "timestamp": message.created_at.isoformat(),
        "channel_id": str(message.channel.id),
        "channel_name": message.channel.name,
        "guild_id": str(message.guild.id),
        "guild_name": message.guild.name
    }

    # Add referenced message info if this is a reply
    if message.reference and message.reference.message_id:
        data["reply_to_message_id"] = str(message.reference.message_id)

        # Include the referenced message content if available (safely check attribute exists)
        ref_msg = getattr(message, 'referenced_message', None)
        if ref_msg is not None:
            data["referenced_message"] = {
                "id": str(ref_msg.id),
                "author": ref_msg.author.display_name,
                "author_id": str(ref_msg.author.id),
                "content": ref_msg.content,
                "timestamp": ref_msg.created_at.isoformat()
            }

    return data


def format_message_full(message: discord.Message) -> dict:
    """Format a Discord message with full details (attachments, reactions, etc.)"""
    data = format_message(message)
    data["url"] = message.jump_url
    data["attachments"] = [
        {
            "filename": att.filename,
            "url": att.url,
            "size": att.size
        } for att in message.attachments
    ]
    data["embeds"] = len(message.embeds)
    data["reactions"] = [
        {
            "emoji": str(reaction.emoji),
            "count": reaction.count
        } for reaction in message.reactions
    ]
    return data


def format_user(member: discord.Member, include_roles: bool = False) -> dict:
    """Format a Discord member into a consistent dictionary structure

    Args:
        member: Discord member object
        include_roles: If True, includes joined_at and roles (for detailed user info)
    """
    data = {
        "id": str(member.id),
        "username": member.name,
        "display_name": member.display_name,
        "discriminator": member.discriminator,
        "is_bot": member.bot,
        "status": str(member.status) if member.status else "offline",
        "avatar_url": str(member.avatar.url) if member.avatar else None,
        "mention": member.mention
    }
    if include_roles:
        data["joined_at"] = member.joined_at.isoformat() if member.joined_at else None
        data["roles"] = [role.name for role in member.roles if role.name != "@everyone"]
    return data


def format_channel(channel: discord.TextChannel) -> dict:
    """Format a Discord text channel into a dictionary"""
    return {
        "id": str(channel.id),
        "name": channel.name,
        "type": "text",
        "guild_id": str(channel.guild.id),
        "guild_name": channel.guild.name
    }


def format_thread(thread: discord.Thread) -> dict:
    """Format a Discord thread into a dictionary"""
    return {
        "id": str(thread.id),
        "name": f"🧵 {thread.name}",
        "type": "thread",
        "parent_id": str(thread.parent_id),
        "parent_name": thread.parent.name if thread.parent else None,
        "guild_id": str(thread.guild.id),
        "guild_name": thread.guild.name,
        "archived": thread.archived,
        "member_count": thread.member_count or 0
    }
