"""
Memory Service - PostgreSQL JSONB Storage

Manages user personal memories using PostgreSQL with JSONB format.
Auto-creates database and handles connection issues.
"""

import logging
import json
import time
from typing import Dict, List, Any
import psycopg2
from psycopg2 import OperationalError, sql
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
    RETRY_DELAY = 1
    
    def __init__(self):
        """Initialize PostgreSQL connection and LLM client"""
        self.conn = None
        self._last_connection_attempt = 0
        self._connection_cooldown = 5  # seconds between reconnection attempts
        self._db_config = {
            'host': config.POSTGRES_HOST,
            'port': config.POSTGRES_PORT,
            'dbname': config.POSTGRES_DB,
            'user': config.POSTGRES_USER,
            'password': config.POSTGRES_PASSWORD,
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5
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
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Automatically ensure database and table exist"""
        try:
            temp_config = self._db_config.copy()
            temp_config['dbname'] = 'postgres'
            
            conn = psycopg2.connect(**temp_config)
            conn.autocommit = True
            
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (self._db_config['dbname'],)
                )
                if not cur.fetchone():
                    logger.info(f"Creating database '{self._db_config['dbname']}'...")
                    cur.execute(
                        sql.SQL("CREATE DATABASE {}").format(
                            sql.Identifier(self._db_config['dbname'])
                        )
                    )
                    logger.info(f"Database '{self._db_config['dbname']}' created")
            
            conn.close()
            
        except Exception as e:
            logger.warning(f"Could not auto-create database: {e}")
    
    def _is_connection_valid(self) -> bool:
        """Check if the current connection is still valid"""
        if self.conn is None or self.conn.closed:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return True
        except Exception as e:
            logger.warning(f"Connection validation failed: {e}")
            return False
    
    def _close_connection(self):
        """Safely close the database connection"""
        if self.conn is not None:
            try:
                if not self.conn.closed:
                    self.conn.close()
                    logger.info("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self.conn = None
    
    def _get_connection(self):
        """Get database connection with retry logic and cooldown"""
        import time
        
        current_time = time.time()
        if self._last_connection_attempt > 0:
            time_since_last = current_time - self._last_connection_attempt
            if time_since_last < self._connection_cooldown and not self._is_connection_valid():
                logger.debug(f"Connection cooldown active ({time_since_last:.1f}s / {self._connection_cooldown}s)")
        
        if self._is_connection_valid():
            return self.conn
        
        self._close_connection()
        
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                self._last_connection_attempt = time.time()
                logger.info(f"Connecting to PostgreSQL (attempt {attempt + 1}/{self.MAX_RETRIES})...")
                
                self.conn = psycopg2.connect(**self._db_config)
                self.conn.autocommit = True
                
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
                
                self._init_database()
                logger.info("Database connection established successfully")
                return self.conn
                
            except OperationalError as e:
                last_error = e
                error_msg = str(e).lower()
                
                if "does not exist" in error_msg and "database" in error_msg:
                    logger.error(f"Database '{self._db_config['dbname']}' does not exist. Run ./fix_db.sh to create it.")
                elif "password authentication failed" in error_msg:
                    logger.error(f"Authentication failed. Check POSTGRES_USER and POSTGRES_PASSWORD in .env")
                elif "could not connect" in error_msg or "connection refused" in error_msg:
                    logger.error(f"Cannot reach PostgreSQL server. Ensure Docker container is running: docker compose up -d postgres")
                else:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error connecting to database: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
        
        logger.error(f"Failed to connect to PostgreSQL after {self.MAX_RETRIES} attempts")
        raise ConnectionError(
            f"Cannot connect to PostgreSQL at {self._db_config['host']}:{self._db_config['port']} "
            f"after {self.MAX_RETRIES} attempts. Last error: {last_error}\n\n"
            f"Troubleshooting:\n"
            f"1. Check if PostgreSQL is running: docker ps | grep postgres\n"
            f"2. If not running: docker compose up -d postgres\n"
            f"3. If database issues persist: ./fix_db.sh\n"
            f"4. Check credentials in .env file"
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
                self._get_connection()
                return operation(*args, **kwargs)
            except (OperationalError, psycopg2.InterfaceError) as e:
                last_error = e
                logger.warning(f"Database operation failed (attempt {attempt + 1}): {e}")
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
            current_memories = self.get_user_memories(user_id)
            logger.debug(f"Current memories for {user_id}: {current_memories}")
            
            extraction_result = self._extract_structured_memories(message, current_memories)
            logger.debug(f"Extraction result: {extraction_result}")
            
            if not extraction_result or not extraction_result.get("updates"):
                logger.info(f"No memory updates for user {user_id}")
                return []
            
            updates = extraction_result.get("updates", {})
            logger.info(f"Extracted updates: {updates}")
            
            updated_memories = self._merge_memories(current_memories, updates)
            logger.info(f"Merged memories: {updated_memories}")
            
            self._save_memories(user_id, updated_memories)
            logger.info(f"Saved memories to database for user {user_id}")
            
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
        system_prompt = """Extract ALL personal info from user messages. Return JSON only.

IDENTITY: name, nickname, age, birthday, gender, nationality, ethnicity
LOCATION: location, hometown, timezone, address
WORK: role, company, industry, experience_years, stack, skills[], certifications[], education, career_goals[]
PREFERENCES: likes[], dislikes[], hobbies[], interests[], favorite_foods[], favorite_music[], favorite_movies[], favorite_books[], favorite_games[], favorite_sports[]
LIFESTYLE: diet, exercise, sleep_schedule, work_style, communication_style, morning_person
RELATIONSHIPS: family[], pets[], relationship_status, partner_name, children[]
LANGUAGES: languages[], native_language, learning_languages[]
HEALTH: allergies[], health_conditions[], disabilities[]
PERSONALITY: personality_traits[], values[], life_goals[], fears[], strengths[], weaknesses[]
FINANCE: income_range, financial_goals[]
OTHER: habits[], routines[], memorable_facts[], achievements[], travel_history[], bucket_list[]

RULES:
- Extract EVERYTHING personal mentioned
- Lists use arrays: {"skills": ["Python", "Java"]}
- Single values use strings: {"name": "John"}
- Negative statements use "remove_" prefix: {"remove_skills": ["React"]}
- Create new fields if needed for unique info
- Skip: temporary states, current tasks, questions without personal info

EXAMPLES:
{"name": "John", "age": 28, "birthday": "March 15"}
{"role": "developer", "company": "Google", "skills": ["Python"], "experience_years": 5}
{"likes": ["pizza", "hiking"], "dislikes": ["tomatoes"], "hobbies": ["hiking", "reading"]}
{"pets": ["dog named Max"], "family": ["wife Sarah", "son aged 3"]}
{"languages": ["English", "Spanish"], "learning_languages": ["Japanese"]}
{"diet": "vegetarian", "allergies": ["nuts", "shellfish"]}
{"remove_skills": ["Java"]} (when user says "I forgot Java")

Return {} if no personal info found."""

        user_prompt = f"""Memories: {json.dumps(current_memories) if current_memories else "{}"}
Message: "{message}"
Extract ALL personal info as JSON:"""

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
            
            for key in updates.keys():
                if key.startswith("remove_"):
                    if not isinstance(updates[key], list):
                        logger.warning(f"Removal value for {key} is not a list, converting: {updates[key]}")
                        updates[key] = [updates[key]] if updates[key] else []
            
            changes = []
            for key, value in updates.items():
                if key.startswith("remove_"):
                    field_name = key[7:]
                    changes.append({
                        "field": field_name,
                        "value": value,
                        "event": "REMOVE"
                    })
                else:
                    event = "UPDATE" if key in current_memories else "ADD"
                    if isinstance(value, list) and key in current_memories and isinstance(current_memories[key], list):
                        existing_normalized = {str(v).lower().strip() for v in current_memories[key]}
                        new_normalized = {str(v).lower().strip() for v in value}
                        if not new_normalized.issubset(existing_normalized):
                            event = "UPDATE"
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
        
        For lists: append unique items OR remove items
        For strings/other: replace
        
        Conflict resolution:
        - If item added to "likes", remove it from "dislikes"
        - If item added to "dislikes", remove it from "likes"
        
        Removals:
        - Keys with "remove_" prefix indicate items to remove from that field
        """
        merged = current.copy()
        
        conflict_pairs = [
            ("likes", "dislikes"),
            ("dislikes", "likes"),
        ]
        
        def normalize_item(item):
            return str(item).lower().strip()
        
        removals_to_process = {}
        normal_updates = {}
        
        for key, value in updates.items():
            if key.startswith("remove_") and isinstance(value, list):
                field_name = key[7:]
                removals_to_process[field_name] = value
            else:
                normal_updates[key] = value
        
        for field_name, items_to_remove in removals_to_process.items():
            logger.info(f"Processing removal: {field_name} -> {items_to_remove}")
            if field_name in merged:
                if isinstance(merged[field_name], list):
                    original_count = len(merged[field_name])
                    items_to_remove_normalized = {normalize_item(item) for item in items_to_remove}
                    logger.debug(f"Items to remove (normalized): {items_to_remove_normalized}")
                    logger.debug(f"Current {field_name} before removal: {merged[field_name]}")
                    
                    merged[field_name] = [
                        item for item in merged[field_name]
                        if normalize_item(item) not in items_to_remove_normalized
                    ]
                    
                    removed_count = original_count - len(merged[field_name])
                    logger.info(f"Removed {removed_count} items from {field_name}: {items_to_remove}. Remaining: {merged[field_name]}")
                    
                    if not merged[field_name]:
                        del merged[field_name]
                        logger.info(f"Deleted empty {field_name} field")
                else:
                    current_value = merged[field_name]
                    current_value_normalized = normalize_item(current_value)
                    items_to_remove_normalized = {normalize_item(item) for item in items_to_remove}
                    
                    if current_value_normalized in items_to_remove_normalized:
                        del merged[field_name]
                        logger.info(f"Deleted {field_name} field (value matched: {current_value})")
                    else:
                        logger.warning(f"Cannot remove from {field_name}: current value '{current_value}' does not match any items to remove: {items_to_remove}")
            else:
                logger.warning(f"Cannot remove from {field_name}: field not found in current memories")
        
        for key, value in normal_updates.items():
            if isinstance(value, list) and value:
                for field, opposite_field in conflict_pairs:
                    if key == field and opposite_field in merged:
                        if isinstance(merged[opposite_field], list):
                            new_values_normalized = {normalize_item(v) for v in value}
                            merged[opposite_field] = [
                                item for item in merged[opposite_field]
                                if normalize_item(item) not in new_values_normalized
                            ]
                            if not merged[opposite_field]:
                                del merged[opposite_field]
        
        for key, value in normal_updates.items():
            if isinstance(value, list):
                if key in merged and isinstance(merged[key], list):
                    existing_normalized = {normalize_item(item) for item in merged[key]}
                    for new_item in value:
                        if normalize_item(new_item) not in existing_normalized:
                            merged[key].append(new_item)
                            existing_normalized.add(normalize_item(new_item))
                else:
                    seen_normalized = set()
                    merged[key] = []
                    for item in value:
                        item_normalized = normalize_item(item)
                        if item_normalized not in seen_normalized:
                            seen_normalized.add(item_normalized)
                            merged[key].append(item)
            else:
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
    
    def get_memory_context(self, user_id: str) -> str:
        """
        Get memory context formatted for AI response generation.
        
        Args:
            user_id: User ID
            
        Returns:
            Formatted memory context string
        """
        memories = self.get_user_memories(user_id)
        
        if not memories:
            return ""
        
        context_parts = ["User Personal Information:"]
        for key, value in memories.items():
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            else:
                value_str = str(value)
            context_parts.append(f"- {key}: {value_str}")
        
        return "\n".join(context_parts)
    
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
        self._close_connection()
