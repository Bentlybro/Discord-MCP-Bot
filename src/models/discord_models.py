from pydantic import BaseModel
from typing import Optional

class MessageResponse(BaseModel):
    id: str
    author: str
    author_id: str
    content: str
    timestamp: str
    channel_id: str
    channel_name: str
    guild_id: str
    guild_name: str

class GetMessagesRequest(BaseModel):
    channel_id: str
    limit: int = 10
    before_message_id: Optional[str] = None

class SearchMessagesRequest(BaseModel):
    channel_id: str
    query: str
    limit: int = 10

class SearchGuildMessagesRequest(BaseModel):
    guild_id: str
    query: str
    limit: int = 50

class GetMessageByUrlRequest(BaseModel):
    message_url: str

class ChannelInfo(BaseModel):
    id: str
    name: str
    type: str
    guild_id: str
    guild_name: str

class SendMessageRequest(BaseModel):
    channel_id: str
    content: str
    reply_to_message_id: Optional[str] = None

class SendMessageResponse(BaseModel):
    success: bool
    message: Optional[MessageResponse] = None
    error: Optional[str] = None

class AskQuestionRequest(BaseModel):
    channel_id: str
    question: str
    timeout: int = 300
    target_user_id: Optional[str] = None

class AskQuestionResponse(BaseModel):
    success: bool
    question_message: Optional[MessageResponse] = None
    response: Optional[MessageResponse] = None
    error: Optional[str] = None
    timeout: Optional[int] = None

class UserInfo(BaseModel):
    id: str
    username: str
    display_name: str
    discriminator: str
    is_bot: bool
    status: str
    joined_at: Optional[str] = None
    roles: Optional[list] = None
    avatar_url: Optional[str] = None
    mention: str

class ListGuildUsersRequest(BaseModel):
    guild_id: str
    include_bots: bool = False

class ListAllUsersRequest(BaseModel):
    include_bots: bool = False

class GuildUsersResponse(BaseModel):
    guild_name: str
    guild_id: str
    total_members: int
    users: list[UserInfo]
    users_returned: int

class AllUsersResponse(BaseModel):
    unique_users: list[UserInfo]
    total_unique_users: int
    guilds: list
    total_guilds: int