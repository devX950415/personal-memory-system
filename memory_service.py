"""
User Personal Memory Service using mem0
This service manages long-term user memories across all chats
"""
from typing import List, Dict, Any, Optional
from mem0 import Memory
from config import config
import logging

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service for managing user personal memories using mem0.
    
    Mem0 handles:
    - Intelligent memory extraction from conversations
    - Semantic search and retrieval
    - Memory updates and deduplication
    - Vector embeddings for context-aware memory
    """
    
    def __init__(self):
        """Initialize mem0 with Azure OpenAI or regular OpenAI backend"""
        # Base configuration for vector store
        mem0_config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "user_memories",
                    "path": "./qdrant_db",  # Local storage
                }
            }
        }
        
        # Configure LLM and Embedder based on provider
        if config.is_azure_openai():
            # Use Azure OpenAI
            logger.info("Configuring mem0 with Azure OpenAI")
            mem0_config["llm"] = {
                "provider": "azure_openai",
                "config": {
                    "model": config.AZURE_OPENAI_MODEL,
                    "azure_deployment": config.AZURE_OPENAI_DEPLOYMENT,
                    "azure_endpoint": config.AZURE_OPENAI_ENDPOINT,
                    "api_key": config.AZURE_OPENAI_API_KEY,
                    "api_version": config.AZURE_OPENAI_API_VERSION,
                    "temperature": 0.1,
                }
            }
            mem0_config["embedder"] = {
                "provider": "azure_openai",
                "config": {
                    "model": config.AZURE_OPENAI_EMBEDDING_MODEL,
                    "azure_deployment": config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                    "azure_endpoint": config.AZURE_OPENAI_EMBEDDING_ENDPOINT,
                    "api_key": config.AZURE_OPENAI_EMBEDDING_API_KEY,
                    "api_version": config.AZURE_OPENAI_EMBEDDING_API_VERSION,
                }
            }
        else:
            # Use regular OpenAI
            logger.info("Configuring mem0 with OpenAI")
            mem0_config["llm"] = {
                "provider": "openai",
                "config": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                    "api_key": config.OPENAI_API_KEY
                }
            }
            mem0_config["embedder"] = {
                "provider": "openai",
                "config": {
                    "model": "text-embedding-3-small",
                    "api_key": config.OPENAI_API_KEY
                }
            }
        
        self.memory = Memory.from_config(mem0_config)
        logger.info("MemoryService initialized with mem0")
    
    def add_memory_from_message(
        self, 
        user_id: str, 
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract and store memories from a user message.
        
        Mem0 will intelligently determine what should be remembered.
        It filters out temporary or non-personal information automatically.
        
        Args:
            user_id: Unique user identifier
            message: User's message to extract memory from
            metadata: Optional metadata to attach to the memory
            
        Returns:
            List of extracted memories
        """
        try:
            # Mem0 will analyze the message and extract only meaningful memories
            memories = self.memory.add(
                messages=message,
                user_id=user_id,
                metadata=metadata or {}
            )
            
            logger.info(f"Extracted {len(memories)} memories for user {user_id}")
            return memories
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return []
    
    def add_memory_from_conversation(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract memories from a conversation history.
        
        Args:
            user_id: Unique user identifier
            messages: List of messages in format [{"role": "user", "content": "..."}]
            metadata: Optional metadata
            
        Returns:
            List of extracted memories
        """
        try:
            memories = self.memory.add(
                messages=messages,
                user_id=user_id,
                metadata=metadata or {}
            )
            
            logger.info(f"Extracted {len(memories)} memories from conversation for user {user_id}")
            return memories
        except Exception as e:
            logger.error(f"Error adding memories from conversation: {e}")
            return []
    
    def get_all_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories for a user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            List of all user memories
        """
        try:
            memories = self.memory.get_all(user_id=user_id)
            logger.info(f"Retrieved {len(memories)} memories for user {user_id}")
            return memories
        except Exception as e:
            logger.error(f"Error getting memories: {e}")
            return []
    
    def search_memories(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search user memories with semantic similarity.
        
        Args:
            user_id: Unique user identifier
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of relevant memories
        """
        try:
            memories = self.memory.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            logger.info(f"Found {len(memories)} memories for query: {query}")
            return memories
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []
    
    def update_memory(
        self, 
        memory_id: str, 
        data: str
    ) -> Dict[str, Any]:
        """
        Update a specific memory.
        
        Args:
            memory_id: ID of the memory to update
            data: New memory content
            
        Returns:
            Updated memory
        """
        try:
            result = self.memory.update(memory_id=memory_id, data=data)
            logger.info(f"Updated memory {memory_id}")
            return result
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            return {}
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory.
        
        Args:
            memory_id: ID of the memory to delete
            
        Returns:
            True if successful
        """
        try:
            self.memory.delete(memory_id=memory_id)
            logger.info(f"Deleted memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False
    
    def delete_all_memories(self, user_id: str) -> bool:
        """
        Delete all memories for a user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            True if successful
        """
        try:
            self.memory.delete_all(user_id=user_id)
            logger.info(f"Deleted all memories for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting all memories: {e}")
            return False
    
    def get_memory_context(self, user_id: str, current_message: str) -> str:
        """
        Get relevant memory context for generating a response.
        
        Args:
            user_id: Unique user identifier
            current_message: Current user message
            
        Returns:
            Formatted memory context string
        """
        # Search for relevant memories based on current message
        relevant_memories = self.search_memories(user_id, current_message, limit=5)
        
        if not relevant_memories:
            return ""
        
        # Format memories as context
        context_parts = ["User Personal Information (from previous conversations):"]
        for mem in relevant_memories:
            context_parts.append(f"- {mem.get('memory', '')}")
        
        return "\n".join(context_parts)

