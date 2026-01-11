"""
Memory Service - PostgreSQL JSONB Storage

Manages user personal memories using PostgreSQL with JSONB format.
No vector embeddings - structured key-value storage.
"""

import logging
import json
from typing import Dict, List, Any
import psycopg2
from psycopg2 import OperationalError
from psycopg2.extras import RealDictCursor, Json
from openai import AzureOpenAI, OpenAI

from config import config

logging.basicConfig(level=config.get_log_level())
logger = logging.getLogger(__name__)


class MemoryService:
    """
    Memory service using PostgreSQL JSONB storage.
    
    Stores memories as structured JSON: {"likes": [...], "dislikes": [...], "role": "...", etc}
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self):
        """Initialize PostgreSQL connection and LLM client"""
        # Database connection will be lazy - only connect when needed
        self.conn = None
        self._db_config = {
            'host': config.POSTGRES_HOST,
            'port': config.POSTGRES_PORT,
            'dbname': config.POSTGRES_DB,
            'user': config.POSTGRES_USER,
            'password': config.POSTGRES_PASSWORD,
            'connect_timeout': 10
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
    
    def _is_connection_valid(self) -> bool:
        """Check if the current connection is still valid"""
        if self.conn is None or self.conn.closed:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    def _get_connection(self, retry_count: int = 0):
        """Get database connection with retry logic"""
        import time
        
        # Check if existing connection is valid
        if self._is_connection_valid():
            return self.conn
        
        # Close stale connection if exists
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
        
        # Try to establish new connection with retries
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"Connecting to PostgreSQL (attempt {attempt + 1}/{self.MAX_RETRIES})...")
                self.conn = psycopg2.connect(**self._db_config)
                self.conn.autocommit = True
                # Create table if not exists on first connection
                self._init_database()
                logger.info("Database connection established")
                return self.conn
            except OperationalError as e:
                last_error = e
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
        
        logger.error(f"Failed to connect to PostgreSQL after {self.MAX_RETRIES} attempts")
        raise ConnectionError(
            f"Cannot connect to PostgreSQL at {self._db_config['host']}:{self._db_config['port']} "
            f"after {self.MAX_RETRIES} attempts. Please ensure PostgreSQL is running. Error: {last_error}"
        )
    
    def _init_database(self):
        """Create memories table if it doesn't exist"""
        with self.conn.cursor() as cur:
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
    
    def _execute_with_retry(self, operation, *args, **kwargs):
        """Execute a database operation with automatic reconnection on failure"""
        import time
        
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                # Ensure we have a valid connection
                self._get_connection()
                return operation(*args, **kwargs)
            except (OperationalError, psycopg2.InterfaceError) as e:
                last_error = e
                logger.warning(f"Database operation failed (attempt {attempt + 1}): {e}")
                # Invalidate connection so it will be recreated
                self.conn = None
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
        
        raise ConnectionError(f"Database operation failed after {self.MAX_RETRIES} attempts: {last_error}")
    
    def add_memory_from_message(
        self,
        user_id: str,
        message: str
    ) -> List[Dict[str, Any]]:
        """
        Extract structured memories from a message and update user's memory.
        
        Args:
            user_id: User ID
            message: User's message
            
        Returns:
            List of extracted memory updates
        """
        try:
            # Get current memories
            current_memories = self.get_user_memories(user_id)
            logger.debug(f"Current memories for {user_id}: {current_memories}")
            
            # Extract new information using LLM
            extraction_result = self._extract_structured_memories(message, current_memories)
            logger.debug(f"Extraction result: {extraction_result}")
            
            if not extraction_result or not extraction_result.get("updates"):
                logger.info(f"No memory updates for user {user_id}")
                return []
            
            updates = extraction_result.get("updates", {})
            logger.info(f"Extracted updates: {updates}")
            
            # Merge updates into current memories
            updated_memories = self._merge_memories(current_memories, updates)
            logger.info(f"Merged memories: {updated_memories}")
            
            # Save to database
            self._save_memories(user_id, updated_memories)
            logger.info(f"Saved memories to database for user {user_id}")
            
            # Format response
            changes = extraction_result.get("changes", [])
            logger.info(f"Updated {len(changes)} memory fields for user {user_id}: {[c.get('field') + ' (' + c.get('event') + ')' for c in changes]}")
            
            return changes
            
        except Exception as e:
            logger.error(f"Error adding memory: {e}", exc_info=True)
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
- and other personal information that is long-term and permanent such as habbit, regular rules and so on

CRITICAL REMOVAL RULES - READ CAREFULLY:
When user says something NEGATIVE about an item that EXISTS in current memories, you MUST use "remove_" prefix:

1. SKILLS REMOVAL - Use "remove_skills" when user says:
   - "I am not good at X" → {"remove_skills": ["X"]}
   - "I don't know X" → {"remove_skills": ["X"]}
   - "I'm bad at X" → {"remove_skills": ["X"]}
   - "I no longer use X" → {"remove_skills": ["X"]}
   - "I forgot X" → {"remove_skills": ["X"]}
   - "I stopped using X" → {"remove_skills": ["X"]}

2. LIKES REMOVAL - Use "remove_likes" when user says:
   - "I don't like X anymore" → {"remove_likes": ["X"]}
   - "I hate X" (when X is in likes) → {"remove_likes": ["X"], "dislikes": ["X"]}
   - "I dislike X" (when X is in likes) → {"remove_likes": ["X"], "dislikes": ["X"]}

3. ADDITIONS: If user mentions something positive, add to appropriate list
   - "I love X" → add to "likes"
   - "I know X", "I'm good at X", "I use X" → add to "skills"
   - "I like X" → add to "likes"

4. CONFLICTS:
   - If user says they like something, put it in "likes" (NOT "dislikes")
   - If user says they hate/dislike something, put it in "dislikes" (NOT "likes")
   - When removing from one list due to negative statement, check if it should be added to opposite list

5. FORMAT FOR REMOVALS - CRITICAL:
   - ALWAYS use "remove_" prefix for removals: "remove_skills", "remove_likes", etc.
   - The value MUST be a list: {"remove_skills": ["React"]} NOT {"remove_skills": "React"}
   - Check current memories to see if the item exists before removing

DO NOT EXTRACT:
- Temporary activities (e.g., "doing homework", "watching TV")
- Short-term plans (e.g., "going tomorrow", "meeting next week")
- Current states (e.g., "is tired", "is busy")
- Time-bound information
- Task-specific requests

Output ONLY updates as JSON object. For additions, use normal field names. For removals, ALWAYS use "remove_" prefix.
If no permanent information found, return empty object {}

Examples:
- "My name is John" → {"name": "John"}
- "I'm a frontend developer" → {"role": "frontend developer", "stack": "frontend"}
- "I like pizza and hate tomatoes" → {"likes": ["pizza"], "dislikes": ["tomatoes"]}
- "I love Python" → {"likes": ["Python"]}
- "I am not good at React" (when current memories have skills: ["React", "Vue"]) → {"remove_skills": ["React"]}
- "I don't know JavaScript anymore" → {"remove_skills": ["JavaScript"]}
- "I hate tomatoes" (when current memories have likes: ["tomatoes"]) → {"remove_likes": ["tomatoes"], "dislikes": ["tomatoes"]}
- "I'm doing homework" → {} (temporary activity, ignore)"""

        user_prompt = f"""Current memories: {json.dumps(current_memories, indent=2)}

New message: "{message}"

IMPORTANT: Check current memories above to see if user is REMOVING something they previously had.

REMOVAL DETECTION:
1. If current memories have "skills": ["X", "Y"] and user says "I am not good at X" or "I don't know X", return: {{"remove_skills": ["X"]}}
2. If current memories have "likes": ["X", "Y"] and user says "I hate X" or "I don't like X", return: {{"remove_likes": ["X"], "dislikes": ["X"]}}
3. Compare the message with current memories - if user mentions something negative about an existing item, REMOVE it.

ADDITION DETECTION:
- For new positive information, use normal field names: {{"skills": ["Z"], "likes": ["W"]}}

CRITICAL: 
- For removals, ALWAYS use "remove_" prefix followed by field name
- Value MUST be a list: ["X"] not "X"
- Check if items exist in current memories before removing
- Return empty {{}} if nothing to extract."""

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
            logger.debug(f"LLM raw response: {result_text}")
            updates = json.loads(result_text)
            logger.info(f"Parsed updates from LLM: {updates}")
            
            if not updates:
                return {"updates": {}, "changes": []}
            
            # Validate removal format
            for key in updates.keys():
                if key.startswith("remove_"):
                    if not isinstance(updates[key], list):
                        logger.warning(f"Removal value for {key} is not a list, converting: {updates[key]}")
                        updates[key] = [updates[key]] if updates[key] else []
            
            # Build list of changes for response
            changes = []
            for key, value in updates.items():
                if key.startswith("remove_"):
                    # This is a removal - extract the actual field name
                    field_name = key[7:]  # Remove "remove_" prefix
                    changes.append({
                        "field": field_name,
                        "value": value,
                        "event": "REMOVE"
                    })
                else:
                    # This is an addition or update
                    event = "UPDATE" if key in current_memories else "ADD"
                    # Check if it's actually a replacement (for list fields)
                    if isinstance(value, list) and key in current_memories and isinstance(current_memories[key], list):
                        # Check if items are being added or if it's a complete replacement
                        existing_normalized = {str(v).lower().strip() for v in current_memories[key]}
                        new_normalized = {str(v).lower().strip() for v in value}
                        if not new_normalized.issubset(existing_normalized):
                            event = "UPDATE"  # Some items are new
                    changes.append({
                        "field": key,
                        "value": value,
                        "event": event
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
        Merge new updates into current memories with conflict resolution and removals.
        
        For lists (likes, dislikes, skills, etc): append unique items OR remove items
        For strings/other: replace
        
        Conflict resolution:
        - If item added to "likes", remove it from "dislikes"
        - If item added to "dislikes", remove it from "likes"
        
        Removals:
        - Keys with "remove_" prefix indicate items to remove from that field
        - Example: {"remove_skills": ["react.js"]} removes "react.js" from skills list
        """
        merged = current.copy()
        
        # Define conflicting field pairs
        conflict_pairs = [
            ("likes", "dislikes"),
            ("dislikes", "likes"),
        ]
        
        # Helper function to normalize items for comparison (case-insensitive)
        def normalize_item(item):
            """Normalize item for comparison"""
            return str(item).lower().strip()
        
        # Step 1: Process removals first (before any additions)
        removals_to_process = {}
        normal_updates = {}
        
        for key, value in updates.items():
            if key.startswith("remove_") and isinstance(value, list):
                # Extract the actual field name (e.g., "remove_skills" -> "skills")
                field_name = key[7:]  # Remove "remove_" prefix
                removals_to_process[field_name] = value
            else:
                normal_updates[key] = value
        
        # Process removals
        for field_name, items_to_remove in removals_to_process.items():
            logger.info(f"Processing removal: {field_name} -> {items_to_remove}")
            if field_name in merged:
                if isinstance(merged[field_name], list):
                    # Handle list field removal
                    original_count = len(merged[field_name])
                    # Normalize items to remove for comparison
                    items_to_remove_normalized = {normalize_item(item) for item in items_to_remove}
                    logger.debug(f"Items to remove (normalized): {items_to_remove_normalized}")
                    logger.debug(f"Current {field_name} before removal: {merged[field_name]}")
                    
                    # Remove items (case-insensitive comparison)
                    merged[field_name] = [
                        item for item in merged[field_name]
                        if normalize_item(item) not in items_to_remove_normalized
                    ]
                    
                    removed_count = original_count - len(merged[field_name])
                    logger.info(f"Removed {removed_count} items from {field_name}: {items_to_remove}. Remaining: {merged[field_name]}")
                    
                    # Clean up empty lists
                    if not merged[field_name]:
                        del merged[field_name]
                        logger.info(f"Deleted empty {field_name} field")
                else:
                    # Handle string/non-list field removal
                    # Check if the current value matches any of the items to remove
                    current_value = merged[field_name]
                    current_value_normalized = normalize_item(current_value)
                    items_to_remove_normalized = {normalize_item(item) for item in items_to_remove}
                    
                    if current_value_normalized in items_to_remove_normalized:
                        # Current value matches - delete the entire field
                        del merged[field_name]
                        logger.info(f"Deleted {field_name} field (value matched: {current_value})")
                    else:
                        logger.warning(f"Cannot remove from {field_name}: current value '{current_value}' does not match any items to remove: {items_to_remove}")
            else:
                logger.warning(f"Cannot remove from {field_name}: field not found in current memories")
        
        # Step 2: Resolve conflicts for additions (before merging)
        for key, value in normal_updates.items():
            if isinstance(value, list) and value:
                # Check for conflicts with this field
                for field, opposite_field in conflict_pairs:
                    if key == field and opposite_field in merged:
                        # Remove items from opposite field if they're being added to this field
                        if isinstance(merged[opposite_field], list):
                            # Normalize new values for comparison
                            new_values_normalized = {normalize_item(v) for v in value}
                            # Filter out conflicting items (case-insensitive comparison)
                            merged[opposite_field] = [
                                item for item in merged[opposite_field]
                                if normalize_item(item) not in new_values_normalized
                            ]
                            # Clean up empty lists
                            if not merged[opposite_field]:
                                del merged[opposite_field]
        
        # Step 3: Merge normal updates (additions)
        for key, value in normal_updates.items():
            if isinstance(value, list):
                # For lists, merge and deduplicate (case-insensitive)
                if key in merged and isinstance(merged[key], list):
                    # Start with existing items
                    existing_normalized = {normalize_item(item) for item in merged[key]}
                    # Add new items that don't already exist (case-insensitive)
                    for new_item in value:
                        if normalize_item(new_item) not in existing_normalized:
                            merged[key].append(new_item)
                            existing_normalized.add(normalize_item(new_item))
                else:
                    # New list, just deduplicate the updates themselves
                    seen_normalized = set()
                    merged[key] = []
                    for item in value:
                        item_normalized = normalize_item(item)
                        if item_normalized not in seen_normalized:
                            seen_normalized.add(item_normalized)
                            merged[key].append(item)
            else:
                # For other types, replace
                merged[key] = value
        
        return merged
    
    def _save_memories(self, user_id: str, memories: Dict[str, Any]):
        """Save memories to PostgreSQL"""
        def _do_save():
            logger.debug(f"Saving memories for {user_id}: {memories}")
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
                logger.info(f"Successfully saved memories to database for user {user_id}")
        
        self._execute_with_retry(_do_save)
    
    def get_user_memories(self, user_id: str) -> Dict[str, Any]:
        """
        Get all memories for a user.
        
        Returns:
            Dictionary of memories (empty dict if no memories)
        """
        def _do_get():
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
        
        try:
            return self._execute_with_retry(_do_get)
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
        def _do_get_all():
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
        
        try:
            return self._execute_with_retry(_do_get_all)
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
        def _do_delete():
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
        
        try:
            return self._execute_with_retry(_do_delete)
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
        def _do_delete_all():
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_memories WHERE user_id = %s",
                    (user_id,)
                )
                logger.info(f"Deleted all memories for user {user_id}")
                return True
        
        try:
            return self._execute_with_retry(_do_delete_all)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error deleting memories: {e}")
            return False
    
    def __del__(self):
        """Close database connection on cleanup"""
        if hasattr(self, 'conn') and self.conn is not None and not self.conn.closed:
            try:
                self.conn.close()
            except Exception:
                # Ignore errors during cleanup
                pass
