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

class ChannelInfo(BaseModel):
    id: str
    name: str
    type: str
    guild_id: str
    guild_name: str