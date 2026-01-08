"""
PersonalMem Application
Main application integrating chat history and user memory
"""
from typing import List, Dict, Any, Optional
import logging

from config import config
from memory_service import MemoryService
from chat_service import ChatService
from models import MessageRole

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class PersonalMemApp:
    """
    Main application that coordinates chat history and personal memory.
    
    This class demonstrates how to:
    1. Maintain isolated chat histories per chat session
    2. Maintain shared personal memory across all chats for a user
    3. Generate responses using both chat context and personal memory
    """
    
    def __init__(self):
        """Initialize services"""
        self.memory_service = MemoryService()
        self.chat_service = ChatService()
        logger.info("PersonalMemApp initialized")
    
    def create_new_chat(self, user_id: str, title: Optional[str] = None) -> str:
        """
        Create a new chat session for a user.
        
        Args:
            user_id: User ID
            title: Optional chat title
            
        Returns:
            Chat ID
        """
        chat = self.chat_service.create_chat(user_id, title)
        return chat.chat_id
    
    def process_user_message(
        self, 
        user_id: str, 
        chat_id: str, 
        message: str,
        extract_memory: bool = True
    ) -> Dict[str, Any]:
        """
        Process a user message within a chat.
        
        Steps:
        1. Add user message to chat history
        2. Extract and store personal memories (if enabled)
        3. Retrieve relevant personal memories
        4. Generate context for AI response
        
        Args:
            user_id: User ID
            chat_id: Chat ID
            message: User's message
            extract_memory: Whether to extract memories from this message
            
        Returns:
            Dictionary with context and extracted memories
        """
        # Step 1: Add message to chat history
        self.chat_service.add_message(chat_id, MessageRole.USER, message)
        
        # Step 2: Extract memories if enabled
        extracted_memories = []
        if extract_memory:
            extracted_memories = self.memory_service.add_memory_from_message(
                user_id=user_id,
                message=message,
                metadata={"chat_id": chat_id}
            )
        
        # Step 3: Get relevant memories for context
        memory_context = self.memory_service.get_memory_context(user_id, message)
        
        # Step 4: Get chat history
        chat_history = self.chat_service.get_chat_messages_as_dict(chat_id)
        
        return {
            "chat_history": chat_history,
            "memory_context": memory_context,
            "extracted_memories": extracted_memories,
            "user_id": user_id,
            "chat_id": chat_id
        }
    
    def add_assistant_response(
        self, 
        chat_id: str, 
        response: str
    ) -> bool:
        """
        Add an assistant response to the chat.
        
        Args:
            chat_id: Chat ID
            response: Assistant's response
            
        Returns:
            True if successful
        """
        return self.chat_service.add_message(
            chat_id, 
            MessageRole.ASSISTANT, 
            response
        )
    
    def get_user_context(self, user_id: str, chat_id: str) -> str:
        """
        Get complete context for generating a response.
        Combines chat history and personal memory.
        
        Args:
            user_id: User ID
            chat_id: Chat ID
            
        Returns:
            Formatted context string
        """
        # Get chat history
        chat_messages = self.chat_service.get_chat_history(chat_id)
        
        # Get all personal memories
        memories = self.memory_service.get_all_memories(user_id)
        
        # Format context
        context_parts = []
        
        if memories:
            context_parts.append("=== User Personal Information ===")
            for mem in memories:
                context_parts.append(f"- {mem.get('memory', '')}")
            context_parts.append("")
        
        context_parts.append("=== Current Chat History ===")
        for msg in chat_messages:
            context_parts.append(f"{msg.role.upper()}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def get_all_user_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all personal memories for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of memory dictionaries
        """
        return self.memory_service.get_all_memories(user_id)
    
    def delete_user_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            True if successful
        """
        return self.memory_service.delete_memory(memory_id)
    
    def delete_all_user_memories(self, user_id: str) -> bool:
        """
        Delete all memories for a user (memory opt-out).
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        return self.memory_service.delete_all_memories(user_id)
    
    def get_user_chats(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all chats for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of chat dictionaries
        """
        chats = self.chat_service.get_user_chats(user_id)
        return [
            {
                "chat_id": chat.chat_id,
                "title": chat.title,
                "created_at": chat.created_at,
                "message_count": len(chat.messages)
            }
            for chat in chats
        ]
    
    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat and all its messages.
        Note: This does NOT delete personal memories.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            True if successful
        """
        return self.chat_service.delete_chat(chat_id)


# Example usage and demo
def demo():
    """
    Demonstration of the PersonalMem system behavior.
    Shows how memories persist across chats while chat history remains isolated.
    """
    print("=" * 60)
    print("PersonalMem System Demo")
    print("=" * 60)
    
    # Initialize app
    app = PersonalMemApp()
    user_id = "user_honda"
    
    # === CHAT A ===
    print("\n--- CHAT A: User introduces themselves ---")
    chat_a_id = app.create_new_chat(user_id, "Chat A - Introduction")
    print(f"Created Chat A: {chat_a_id}")
    
    # User says their name
    result = app.process_user_message(
        user_id=user_id,
        chat_id=chat_a_id,
        message="My name is Honda. I'm a software engineer who loves Python."
    )
    print(f"Extracted memories: {len(result['extracted_memories'])}")
    
    # Simulate assistant response
    app.add_assistant_response(
        chat_a_id,
        "Nice to meet you, Honda! Python is a great language for software engineering."
    )
    
    # Another message in Chat A
    result = app.process_user_message(
        user_id=user_id,
        chat_id=chat_a_id,
        message="I prefer working on backend systems."
    )
    
    # === CHAT B ===
    print("\n--- CHAT B: New chat (should remember name) ---")
    chat_b_id = app.create_new_chat(user_id, "Chat B - Memory Test")
    print(f"Created Chat B: {chat_b_id}")
    
    # User asks about their name - should retrieve from memory
    result = app.process_user_message(
        user_id=user_id,
        chat_id=chat_b_id,
        message="What is my name?",
        extract_memory=False  # Just asking, not sharing new info
    )
    
    print("\nMemory context available for response:")
    print(result['memory_context'])
    
    # The assistant should respond: "Your name is Honda."
    app.add_assistant_response(
        chat_b_id,
        "Your name is Honda."
    )
    
    # === CHAT C ===
    print("\n--- CHAT C: Testing task-specific context (should NOT save) ---")
    chat_c_id = app.create_new_chat(user_id, "Chat C - Debugging Help")
    print(f"Created Chat C: {chat_c_id}")
    
    # Task-specific message - should not be saved to memory
    result = app.process_user_message(
        user_id=user_id,
        chat_id=chat_c_id,
        message="I need help debugging this function: def add(a, b): return a - b",
        extract_memory=True  # mem0 should filter this out automatically
    )
    print(f"Extracted memories (should be 0 or minimal): {len(result['extracted_memories'])}")
    
    # === Show all memories ===
    print("\n--- All Personal Memories for User ---")
    all_memories = app.get_all_user_memories(user_id)
    for i, mem in enumerate(all_memories, 1):
        print(f"{i}. {mem.get('memory', '')}")
    
    # === Show chat separation ===
    print("\n--- Chat Isolation Check ---")
    print(f"Chat A messages: {len(app.chat_service.get_chat_history(chat_a_id))}")
    print(f"Chat B messages: {len(app.chat_service.get_chat_history(chat_b_id))}")
    print(f"Chat C messages: {len(app.chat_service.get_chat_history(chat_c_id))}")
    
    # === List all user chats ===
    print("\n--- All User Chats ---")
    user_chats = app.get_user_chats(user_id)
    for chat in user_chats:
        print(f"- {chat['title']}: {chat['message_count']} messages")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Validate configuration before running
    try:
        config.validate()
        demo()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease create a .env file with required settings.")
        print("See README.md for setup instructions.")

