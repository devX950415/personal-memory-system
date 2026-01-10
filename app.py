"""
PersonalMem Application

Main application logic focusing on:
- Personal memory management (per-user, persistent)
- Automatic memory extraction from user messages
"""

from typing import Dict, List, Any
import logging

from memory_service import MemoryService
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PersonalMemApp:
    """
    Main application for personal memory management.
    
    Key principles:
    1. Only user personal memory is stored
    2. No chat history is saved
    3. Memory extraction is intelligent and automatic
    """
    
    def __init__(self):
        """Initialize application with memory service only"""
        self.memory_service = MemoryService()
        logger.info("PersonalMemApp initialized")
    
    def process_user_message(
        self, 
        user_id: str, 
        message: str
    ) -> Dict[str, Any]:
        """
        Process a user message.
        
        Steps:
        1. Automatically analyze and extract personal memories (LLM decides)
        2. Retrieve relevant personal memories
        3. Generate context for AI response
        
        Args:
            user_id: User ID
            message: User's message
            
        Returns:
            Dictionary with context and extracted memories
        """
        # Step 1: Automatically extract memories
        extracted_memories = self.memory_service.add_memory_from_message(
            user_id=user_id,
            message=message
        )
        
        # Step 2: Get relevant memories for context
        memory_context = self.memory_service.get_memory_context(user_id, message)
        
        return {
            "memory_context": memory_context,
            "extracted_memories": extracted_memories,
            "user_id": user_id
        }
    
    def get_all_user_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of all user memories
        """
        return self.memory_service.get_all_memories(user_id)
    
    def search_user_memories(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search user memories with semantic similarity.
        
        Args:
            user_id: User ID
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of relevant memories
        """
        return self.memory_service.search_memories(user_id, query, limit)
    
    def delete_user_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory.
        
        Args:
            memory_id: Memory ID to delete
            
        Returns:
            True if successful
        """
        return self.memory_service.delete_memory(memory_id)
    
    def delete_all_user_memories(self, user_id: str) -> bool:
        """
        Delete all memories for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        return self.memory_service.delete_all_memories(user_id)
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete context for generating AI response.
        
        Args:
            user_id: User ID
            
        Returns:
            Complete context dictionary
        """
        user_memories = self.memory_service.get_all_memories(user_id)
        
        return {
            "user_memories": user_memories,
            "user_id": user_id
        }


def demo():
    """
    Demo showcasing the PersonalMem system capabilities.
    
    Demonstrates:
    1. Personal memory is stored per-user
    2. Automatic memory extraction (permanent info only)
    3. No chat history is saved
    """
    print("=" * 60)
    print("PersonalMem System Demo")
    print("=" * 60)
    
    # Initialize app
    app = PersonalMemApp()
    user_id = "user_honda"
    
    # === Message 1 ===
    print("\n--- Message 1: User introduces themselves ---")
    result = app.process_user_message(
        user_id=user_id,
        message="My name is Honda. I'm a software engineer who loves Python."
    )
    print(f"Extracted memories: {len(result['extracted_memories'])}")
    for mem in result['extracted_memories']:
        print(f"  - {mem.get('memory', '')}")
    
    # === Message 2 ===
    print("\n--- Message 2: User shares preference ---")
    result = app.process_user_message(
        user_id=user_id,
        message="I prefer working on backend systems."
    )
    print(f"Extracted memories: {len(result['extracted_memories'])}")
    for mem in result['extracted_memories']:
        print(f"  - {mem.get('memory', '')}")
    
    # === Message 3 ===
    print("\n--- Message 3: User asks question (should retrieve from memory) ---")
    result = app.process_user_message(
        user_id=user_id,
        message="What is my name?"
    )
    print(f"Extracted memories: {len(result['extracted_memories'])} (should be 0)")
    print("\nMemory context available for response:")
    print(result['memory_context'])
    
    # === Message 4 ===
    print("\n--- Message 4: Task-specific (should NOT save) ---")
    result = app.process_user_message(
        user_id=user_id,
        message="I need help debugging this function: def add(a, b): return a - b"
    )
    print(f"Extracted memories: {len(result['extracted_memories'])} (should be 0)")
    
    # === Message 5 ===
    print("\n--- Message 5: Temporary activity (should NOT save) ---")
    result = app.process_user_message(
        user_id=user_id,
        message="I'm doing my homework right now"
    )
    print(f"Extracted memories: {len(result['extracted_memories'])} (should be 0)")
    
    # === Show all memories ===
    print("\n--- All Personal Memories for User ---")
    all_memories = app.get_all_user_memories(user_id)
    for i, mem in enumerate(all_memories, 1):
        print(f"{i}. {mem.get('memory', '')}")
    
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
