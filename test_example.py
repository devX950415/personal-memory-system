"""
Example tests for PersonalMem System

Run with: pytest test_example.py
"""
import pytest
from datetime import datetime
from models import Chat, Message, MessageRole


class TestModels:
    """Test data models"""
    
    def test_message_creation(self):
        """Test creating a message"""
        message = Message(
            role=MessageRole.USER,
            content="Hello, world!"
        )
        
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert isinstance(message.timestamp, datetime)
    
    def test_chat_creation(self):
        """Test creating a chat"""
        chat = Chat(
            chat_id="test_chat_123",
            user_id="user_456",
            title="Test Chat"
        )
        
        assert chat.chat_id == "test_chat_123"
        assert chat.user_id == "user_456"
        assert chat.title == "Test Chat"
        assert len(chat.messages) == 0
    
    def test_chat_to_dict(self):
        """Test converting chat to dictionary"""
        chat = Chat(
            chat_id="test_chat",
            user_id="test_user",
            title="Test"
        )
        
        chat_dict = chat.to_dict()
        
        assert chat_dict["chat_id"] == "test_chat"
        assert chat_dict["user_id"] == "test_user"
        assert "messages" in chat_dict
        assert isinstance(chat_dict["messages"], list)


# Integration tests would require MongoDB and mem0 setup
# Example structure:

class TestChatService:
    """Test chat service (requires MongoDB)"""
    
    @pytest.mark.integration
    def test_create_chat(self):
        """Test creating a chat in MongoDB"""
        # This would require actual MongoDB connection
        # from chat_service import ChatService
        # service = ChatService()
        # chat = service.create_chat("user_123", "Test Chat")
        # assert chat.chat_id is not None
        pass


class TestMemoryService:
    """Test memory service (requires mem0 and OpenAI)"""
    
    @pytest.mark.integration
    def test_add_memory(self):
        """Test adding a memory"""
        # This would require actual mem0 setup
        # from memory_service import MemoryService
        # service = MemoryService()
        # memories = service.add_memory_from_message(
        #     "user_123",
        #     "My name is Honda"
        # )
        # assert len(memories) > 0
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

