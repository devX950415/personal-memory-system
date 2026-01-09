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
        # Determine embedding dimensions based on model
        # text-embedding-3-large = 3072, text-embedding-3-small = 1536, text-embedding-ada-002 = 1536
        embedding_dims = 1536  # default
        if config.is_azure_openai() and config.AZURE_OPENAI_EMBEDDING_MODEL:
            if "large" in config.AZURE_OPENAI_EMBEDDING_MODEL.lower():
                embedding_dims = 3072
            elif "small" in config.AZURE_OPENAI_EMBEDDING_MODEL.lower():
                embedding_dims = 1536
        
        # Base configuration for vector store
        mem0_config = {
            "version": "v1.1",  # Use v1.1 API to get proper return format with memories
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "user_memories",
                    "path": "./qdrant_db",  # Local storage
                    "embedding_model_dims": embedding_dims,  # Set correct dimensions
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
                    "temperature": 0.1,
                    "azure_kwargs": {
                        "api_key": config.AZURE_OPENAI_API_KEY,
                        "azure_deployment": config.AZURE_OPENAI_DEPLOYMENT,
                        "azure_endpoint": config.AZURE_OPENAI_ENDPOINT,
                        "api_version": config.AZURE_OPENAI_API_VERSION,
                    }
                }
            }
            mem0_config["embedder"] = {
                "provider": "azure_openai",
                "config": {
                    "model": config.AZURE_OPENAI_EMBEDDING_MODEL,
                    "azure_kwargs": {
                        "api_key": config.AZURE_OPENAI_EMBEDDING_API_KEY,
                        "azure_deployment": config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                        "azure_endpoint": config.AZURE_OPENAI_EMBEDDING_ENDPOINT,
                        "api_version": config.AZURE_OPENAI_EMBEDDING_API_VERSION,
                    }
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
        
        # Patch Azure OpenAI LLM for newer models that require max_completion_tokens
        if config.is_azure_openai():
            self._patch_azure_openai_for_newer_models()
        
        # Patch Qdrant vector store for newer qdrant-client API
        self._patch_qdrant_for_newer_api()
        
        logger.info("MemoryService initialized with mem0")
    
    def _patch_azure_openai_for_newer_models(self):
        """
        Patch mem0's Azure OpenAI LLM to use max_completion_tokens instead of max_tokens
        for newer Azure models like gpt-5.1 that don't support max_tokens.
        """
        try:
            from mem0.llms.azure_openai import AzureOpenAILLM
            
            # Store original method
            original_generate = AzureOpenAILLM.generate_response
            
            def patched_generate_response(self, messages, response_format=None, tools=None, tool_choice="auto"):
                """Patched version that uses max_completion_tokens for newer models"""
                params = {
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p,
                }
                
                # Check if model requires max_completion_tokens (newer Azure models)
                # Models like gpt-5.1, o1, etc. require max_completion_tokens
                model_name = (self.config.model or "").lower()
                if any(new_model in model_name for new_model in ["gpt-5", "o1", "o3"]):
                    # Use max_completion_tokens for newer models
                    params["max_completion_tokens"] = self.config.max_tokens
                else:
                    # Use max_tokens for older models
                    params["max_tokens"] = self.config.max_tokens
                
                if response_format:
                    params["response_format"] = response_format
                if tools:
                    params["tools"] = tools
                    params["tool_choice"] = tool_choice
                
                response = self.client.chat.completions.create(**params)
                return self._parse_response(response, tools)
            
            # Patch the class method
            AzureOpenAILLM.generate_response = patched_generate_response
            logger.info("Patched Azure OpenAI LLM to support max_completion_tokens for newer models")
            
        except Exception as e:
            logger.warning(f"Could not patch Azure OpenAI LLM: {e}. Some newer models may not work correctly.")
    
    def _patch_qdrant_for_newer_api(self):
        """
        Patch mem0's Qdrant vector store to use query_points() instead of search()
        for newer qdrant-client versions (1.16+).
        """
        try:
            from mem0.vector_stores.qdrant import Qdrant
            from qdrant_client.http.models.models import NearestQuery
            
            # Store original search method
            original_search = Qdrant.search
            
            def patched_search(self, query: list, limit: int = 5, filters: dict = None) -> list:
                """Patched version that uses query_points() for newer qdrant-client"""
                try:
                    # Check if client has the old search method
                    if hasattr(self.client, 'search'):
                        # Use old API
                        return original_search(self, query, limit, filters)
                    elif hasattr(self.client, 'query_points'):
                        # Use new API (qdrant-client 1.16+)
                        query_filter = self._create_filter(filters) if filters else None
                        
                        # Create NearestQuery - nearest should be the vector list directly
                        nearest_query = NearestQuery(nearest=query)
                        
                        response = self.client.query_points(
                            collection_name=self.collection_name,
                            query=nearest_query,
                            query_filter=query_filter,
                            limit=limit,
                            with_payload=True,
                            with_vectors=False
                        )
                        
                        # Return ScoredPoint objects directly (matching old search() format)
                        # mem0 expects objects with .id, .payload, and .score attributes
                        return response.points
                    else:
                        # Fall back to original
                        return original_search(self, query, limit, filters)
                except Exception as e:
                    logger.warning(f"Error in patched Qdrant search: {e}, falling back to original")
                    try:
                        return original_search(self, query, limit, filters)
                    except:
                        return []
            
            # Patch the method
            Qdrant.search = patched_search
            logger.info("Patched Qdrant vector store to support newer qdrant-client API")
            
        except Exception as e:
            logger.warning(f"Could not patch Qdrant vector store: {e}. Search may not work correctly.")
    
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
            result = self.memory.add(
                messages=message,
                user_id=user_id,
                metadata=metadata or {}
            )
            
            # Handle return format from mem0
            # v1.1 format: {"results": [memories], "relations": [...]}
            # Old format: {"message": "ok"} (shouldn't happen with v1.1 but handle it)
            if isinstance(result, dict):
                if "results" in result:
                    # v1.1 format - extract the results list
                    memories = result.get("results", [])
                elif "message" in result:
                    # Old format fallback
                    logger.warning("mem0 returned old format. Memories were extracted but format is deprecated.")
                    memories = []
                else:
                    logger.warning(f"Unexpected mem0.add() return format: {result}")
                    memories = []
            elif isinstance(result, list):
                # Direct list return (shouldn't happen but handle it)
                memories = result
            else:
                logger.warning(f"Unexpected mem0.add() return type: {type(result)}")
                memories = []
            
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
            result = self.memory.add(
                messages=messages,
                user_id=user_id,
                metadata=metadata or {}
            )
            
            # Handle return format from mem0 (same as add_memory_from_message)
            if isinstance(result, dict):
                if "results" in result:
                    memories = result.get("results", [])
                elif "message" in result:
                    logger.warning("mem0 returned old format. Memories were extracted but format is deprecated.")
                    memories = []
                else:
                    logger.warning(f"Unexpected mem0.add() return format: {result}")
                    memories = []
            elif isinstance(result, list):
                memories = result
            else:
                logger.warning(f"Unexpected mem0.add() return type: {type(result)}")
                memories = []
            
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
            result = self.memory.get_all(user_id=user_id)
            
            # Handle v1.1 format: {"results": [memories], "relations": [...]}
            if isinstance(result, dict) and "results" in result:
                memories = result.get("results", [])
            elif isinstance(result, list):
                # Old format (shouldn't happen with v1.1 but handle it)
                memories = result
            else:
                logger.warning(f"Unexpected mem0.get_all() return format: {type(result)}")
                memories = []
            
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
            result = self.memory.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            
            # Handle v1.1 format: {"results": [memories], "relations": [...]}
            if isinstance(result, dict) and "results" in result:
                memories = result.get("results", [])
            elif isinstance(result, list):
                # Old format (shouldn't happen with v1.1 but handle it)
                memories = result
            else:
                logger.warning(f"Unexpected mem0.search() return format: {type(result)}")
                memories = []
            
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
            # Handle both dict and string formats
            if isinstance(mem, dict):
                memory_text = mem.get('memory', '')
            elif isinstance(mem, str):
                memory_text = mem
            else:
                memory_text = str(mem)
            if memory_text:
                context_parts.append(f"- {memory_text}")
        
        return "\n".join(context_parts)

