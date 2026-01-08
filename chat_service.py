"""
Chat History Service
This service manages per-chat conversation history
"""
from typing import List, Optional, Dict, Any
from pymongo import MongoClient, DESCENDING
from datetime import datetime
import uuid
import logging

from config import config
from models import Chat, Message, MessageRole

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for managing chat sessions and their message history.
    
    Each chat is isolated - messages are never shared across chats.
    """
    
    def __init__(self):
        """Initialize MongoDB connection"""
        self.client = MongoClient(config.MONGODB_URI)
        self.db = self.client[config.MONGODB_DATABASE]
        self.chats_collection = self.db["chats"]
        
        # Create indexes
        self.chats_collection.create_index("chat_id", unique=True)
        self.chats_collection.create_index([("user_id", 1), ("created_at", DESCENDING)])
        
        logger.info("ChatService initialized with MongoDB")
    
    def create_chat(
        self, 
        user_id: str, 
        title: Optional[str] = None,
        chat_id: Optional[str] = None
    ) -> Chat:
        """
        Create a new chat session.
        
        Args:
            user_id: User ID who owns this chat
            title: Optional chat title
            chat_id: Optional custom chat ID (auto-generated if not provided)
            
        Returns:
            New Chat object
        """
        if chat_id is None:
            chat_id = str(uuid.uuid4())
        
        chat = Chat(
            chat_id=chat_id,
            user_id=user_id,
            title=title or f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        )
        
        self.chats_collection.insert_one(chat.to_dict())
        logger.info(f"Created chat {chat_id} for user {user_id}")
        
        return chat
    
    def get_chat(self, chat_id: str) -> Optional[Chat]:
        """
        Get a chat by ID.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            Chat object or None if not found
        """
        chat_data = self.chats_collection.find_one({"chat_id": chat_id})
        
        if not chat_data:
            logger.warning(f"Chat {chat_id} not found")
            return None
        
        return Chat.from_dict(chat_data)
    
    def get_user_chats(
        self, 
        user_id: str, 
        limit: int = 50
    ) -> List[Chat]:
        """
        Get all chats for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of chats to return
            
        Returns:
            List of Chat objects
        """
        chats_data = self.chats_collection.find(
            {"user_id": user_id}
        ).sort("created_at", DESCENDING).limit(limit)
        
        chats = [Chat.from_dict(chat_data) for chat_data in chats_data]
        logger.info(f"Retrieved {len(chats)} chats for user {user_id}")
        
        return chats
    
    def add_message(
        self, 
        chat_id: str, 
        role: MessageRole, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to a chat.
        
        Args:
            chat_id: Chat ID
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata
            
        Returns:
            True if successful
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata
        )
        
        result = self.chats_collection.update_one(
            {"chat_id": chat_id},
            {
                "$push": {"messages": message.dict()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Added {role} message to chat {chat_id}")
            return True
        else:
            logger.warning(f"Failed to add message to chat {chat_id}")
            return False
    
    def get_chat_history(
        self, 
        chat_id: str, 
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Get message history for a chat.
        
        Args:
            chat_id: Chat ID
            limit: Optional limit on number of messages (most recent)
            
        Returns:
            List of Message objects
        """
        chat = self.get_chat(chat_id)
        
        if not chat:
            return []
        
        messages = chat.messages
        
        if limit:
            messages = messages[-limit:]
        
        logger.info(f"Retrieved {len(messages)} messages from chat {chat_id}")
        return messages
    
    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat and all its messages.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            True if successful
        """
        result = self.chats_collection.delete_one({"chat_id": chat_id})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted chat {chat_id}")
            return True
        else:
            logger.warning(f"Chat {chat_id} not found for deletion")
            return False
    
    def update_chat_title(self, chat_id: str, title: str) -> bool:
        """
        Update a chat's title.
        
        Args:
            chat_id: Chat ID
            title: New title
            
        Returns:
            True if successful
        """
        result = self.chats_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"title": title, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated title for chat {chat_id}")
            return True
        else:
            logger.warning(f"Failed to update title for chat {chat_id}")
            return False
    
    def clear_chat_history(self, chat_id: str) -> bool:
        """
        Clear all messages from a chat (but keep the chat).
        
        Args:
            chat_id: Chat ID
            
        Returns:
            True if successful
        """
        result = self.chats_collection.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "messages": [],
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Cleared history for chat {chat_id}")
            return True
        else:
            logger.warning(f"Failed to clear history for chat {chat_id}")
            return False
    
    def get_chat_messages_as_dict(self, chat_id: str) -> List[Dict[str, str]]:
        """
        Get chat messages in format suitable for LLM APIs.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            List of messages in format [{"role": "user", "content": "..."}]
        """
        messages = self.get_chat_history(chat_id)
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

