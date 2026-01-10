"""
Memory Service - PostgreSQL JSONB Storage

Manages user personal memories using PostgreSQL with JSONB format.
No vector embeddings - structured key-value storage.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2 import OperationalError
from psycopg2.extras import RealDictCursor, Json
from openai import AzureOpenAI, OpenAI

from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryService:
    """
    Memory service using PostgreSQL JSONB storage.
    
    Stores memories as structured JSON: {"likes": [...], "dislikes": [...], "role": "...", etc}
    """
    
    def __init__(self):
        """Initialize PostgreSQL connection and LLM client"""
        # Database connection will be lazy - only connect when needed
        self.conn = None
        self._db_config = {
            'host': config.POSTGRES_HOST,
            'port': config.POSTGRES_PORT,
            'dbname': config.POSTGRES_DB,
            'user': config.POSTGRES_USER,
            'password': config.POSTGRES_PASSWORD
        }
        
        # Initialize LLM client for memory extraction
        if config.is_azure_openai():
            self.llm_client = AzureOpenAI(
                api_key=config.AZURE_OPENAI_API_KEY,
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                api_version=config.AZURE_OPENAI_API_VERSION
            )
            self.model = config.AZURE_OPENAI_DEPLOYMENT
        else:
            self.llm_client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.model = "gpt-4o-mini"
        
        logger.info("MemoryService initialized (lazy database connection)")
    
    def _get_connection(self):
        """Get database connection (lazy connection)"""
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(**self._db_config)
                self.conn.autocommit = True
                # Create table if not exists on first connection
                self._init_database()
                logger.info("Database connection established")
            except OperationalError as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                raise ConnectionError(
                    f"Cannot connect to PostgreSQL at {self._db_config['host']}:{self._db_config['port']}. "
                    f"Please ensure PostgreSQL is running. Error: {e}"
                )
        return self.conn
    
    def _init_database(self):
        """Create memories table if it doesn't exist"""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    user_id TEXT PRIMARY KEY,
                    memories JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    updated_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            # Create index for faster queries
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_gin 
                ON user_memories USING GIN (memories)
            """)
            logger.info("Database table initialized")
    
    def add_memory_from_message(
        self,
        user_id: str,
        message: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract structured memories from a message and update user's memory.
        
        Args:
            user_id: User ID
            message: User's message
            metadata: Additional metadata (unused)
            
        Returns:
            List of extracted memory updates
        """
        try:
            # Get current memories
            current_memories = self.get_user_memories(user_id)
            
            # Extract new information using LLM
            extraction_result = self._extract_structured_memories(message, current_memories)
            
            if not extraction_result or not extraction_result.get("updates"):
                logger.info(f"No memory updates for user {user_id}")
                return []
            
            # Merge updates into current memories
            updated_memories = self._merge_memories(current_memories, extraction_result["updates"])
            
            # Save to database
            self._save_memories(user_id, updated_memories)
            
            # Format response
            changes = extraction_result.get("changes", [])
            logger.info(f"Updated {len(changes)} memory fields for user {user_id}")
            
            return changes
            
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return []
    
    def _extract_structured_memories(
        self,
        message: str,
        current_memories: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to extract structured memories from message.
        
        Returns dict with:
        - updates: Dict of memory updates
        - changes: List of changes made
        """
        system_prompt = """You are a memory extraction system. Extract ONLY long-term, permanent personal information.

EXTRACT (permanent attributes only):
- name: User's full name
- role: Profession/job title (e.g., "software engineer", "teacher")
- stack: Technical stack or specialty (e.g., "frontend", "backend", "full-stack")
- skills: List of skills/expertise (e.g., ["Python", "JavaScript"])
- preferences: Long-term preferences
- likes: Things user likes (as list)
- dislikes: Things user dislikes (as list)
- location: Where user is from or lives
- languages: Languages user speaks (as list)

DO NOT EXTRACT:
- Temporary activities (e.g., "doing homework", "watching TV")
- Short-term plans (e.g., "going tomorrow", "meeting next week")
- Current states (e.g., "is tired", "is busy")
- Time-bound information
- Task-specific requests

Output ONLY updates as JSON object. For lists, use array format. For single values, use strings.
If no permanent information found, return empty object {}

Examples:
- "My name is John" → {"name": "John"}
- "I'm a frontend developer" → {"role": "frontend developer", "stack": "frontend"}
- "I like pizza and hate tomatoes" → {"likes": ["pizza"], "dislikes": ["tomatoes"]}
- "I'm doing homework" → {} (temporary activity, ignore)"""

        user_prompt = f"""Current memories: {json.dumps(current_memories, indent=2)}

New message: "{message}"

Extract ONLY permanent personal information as JSON updates. Return empty {{}} if nothing to extract."""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            updates = json.loads(result_text)
            
            if not updates:
                return {"updates": {}, "changes": []}
            
            # Build list of changes for response
            changes = []
            for key, value in updates.items():
                changes.append({
                    "field": key,
                    "value": value,
                    "event": "UPDATE" if key in current_memories else "ADD"
                })
            
            return {
                "updates": updates,
                "changes": changes
            }
            
        except Exception as e:
            logger.error(f"Error extracting memories: {e}")
            return {"updates": {}, "changes": []}
    
    def _merge_memories(
        self,
        current: Dict[str, Any],
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge new updates into current memories.
        
        For lists (likes, dislikes, skills, etc): append unique items
        For strings/other: replace
        """
        merged = current.copy()
        
        for key, value in updates.items():
            if isinstance(value, list):
                # For lists, merge and deduplicate
                if key in merged and isinstance(merged[key], list):
                    merged[key] = list(set(merged[key] + value))
                else:
                    merged[key] = value
            else:
                # For other types, replace
                merged[key] = value
        
        return merged
    
    def _save_memories(self, user_id: str, memories: Dict[str, Any]):
        """Save memories to PostgreSQL"""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_memories (user_id, memories, created_at, updated_at)
                VALUES (%s, %s, now(), now())
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    memories = %s,
                    updated_at = now()
            """, (user_id, Json(memories), Json(memories)))
    
    def get_user_memories(self, user_id: str) -> Dict[str, Any]:
        """
        Get all memories for a user.
        
        Returns:
            Dictionary of memories (empty dict if no memories)
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT memories FROM user_memories WHERE user_id = %s",
                    (user_id,)
                )
                result = cur.fetchone()
                
                if result:
                    return result['memories']
                return {}
                
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error getting memories: {e}")
            return {}
    
    def get_all_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories formatted for API response.
        
        Returns:
            List of memory items with metadata
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT user_id, memories, created_at, updated_at FROM user_memories WHERE user_id = %s",
                    (user_id,)
                )
                result = cur.fetchone()
                
                if not result:
                    return []
                
                # Format as list of individual memory items
                memories_list = []
                for key, value in result['memories'].items():
                    if isinstance(value, list):
                        value_str = ", ".join(str(v) for v in value)
                    else:
                        value_str = str(value)
                    
                    memories_list.append({
                        "id": f"{user_id}_{key}",
                        "memory": f"{key}: {value_str}",
                        "user_id": user_id,
                        "created_at": result['created_at'].isoformat() if result['created_at'] else None,
                        "updated_at": result['updated_at'].isoformat() if result['updated_at'] else None
                    })
                
                logger.info(f"Retrieved {len(memories_list)} memory items for user {user_id}")
                return memories_list
                
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error getting memories: {e}")
            return []
    
    def get_memory_context(self, user_id: str, current_message: str = "") -> str:
        """
        Get memory context formatted for AI response generation.
        
        Args:
            user_id: User ID
            current_message: Current user message (unused, kept for compatibility)
            
        Returns:
            Formatted memory context string
        """
        memories = self.get_user_memories(user_id)
        
        if not memories:
            return ""
        
        # Format memories as readable context
        context_parts = ["User Personal Information:"]
        for key, value in memories.items():
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            else:
                value_str = str(value)
            context_parts.append(f"- {key}: {value_str}")
        
        return "\n".join(context_parts)
    
    def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search memories (returns all for now, no semantic search).
        
        Args:
            user_id: User ID
            query: Search query (unused)
            limit: Max results (unused)
            
        Returns:
            List of memory items
        """
        return self.get_all_memories(user_id)
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory field.
        
        Args:
            memory_id: Format "user_id_field_name"
            
        Returns:
            True if successful
        """
        try:
            parts = memory_id.rsplit("_", 1)
            if len(parts) != 2:
                return False
            
            user_id, field = parts
            
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE user_memories
                    SET memories = memories - %s,
                        updated_at = now()
                    WHERE user_id = %s
                """, (field, user_id))
                
                logger.info(f"Deleted memory field {field} for user {user_id}")
                return True
                
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False
    
    def delete_all_memories(self, user_id: str) -> bool:
        """
        Delete all memories for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_memories WHERE user_id = %s",
                    (user_id,)
                )
                logger.info(f"Deleted all memories for user {user_id}")
                return True
                
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error deleting memories: {e}")
            return False
    
    def __del__(self):
        """Close database connection"""
        if hasattr(self, 'conn') and self.conn is not None and not self.conn.closed:
            try:
                self.conn.close()
            except:
                pass
