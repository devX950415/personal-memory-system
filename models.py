"""
Data models for PersonalMem system
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    """Message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Single message in a chat"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class Chat(BaseModel):
    """Chat session model"""
    chat_id: str
    user_id: str
    title: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "title": self.title,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "metadata": msg.metadata
                }
                for msg in self.messages
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chat":
        """Create Chat from dictionary"""
        messages = [
            Message(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                metadata=msg.get("metadata")
            )
            for msg in data.get("messages", [])
        ]
        
        return cls(
            chat_id=data["chat_id"],
            user_id=data["user_id"],
            title=data.get("title"),
            messages=messages,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            metadata=data.get("metadata")
        )


class MemorySource(str, Enum):
    """Source of memory extraction"""
    EXPLICIT = "explicit"
    INFERRED = "inferred"


class UserMemoryItem(BaseModel):
    """Individual memory item about a user"""
    key: str
    value: str
    source: MemorySource = MemorySource.EXPLICIT
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class UserMemoryProfile(BaseModel):
    """Complete memory profile for a user"""
    user_id: str
    memories: List[UserMemoryItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

