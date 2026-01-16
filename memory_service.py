"""
Memory Service - MongoDB Storage

Manages user personal memories using MongoDB.
Auto-creates database and handles connection issues.
"""

import logging
import json
import time
from typing import Dict, List, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from openai import AzureOpenAI, OpenAI

from config import config

logging.basicConfig(level=config.get_log_level())
logger = logging.getLogger(__name__)


class MemoryService:
    """
    Memory service using MongoDB storage.
    
    Stores memories as structured JSON: {"likes": [...], "dislikes": [...], "role": "...", etc}
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    
    def __init__(self):
        """Initialize MongoDB connection and LLM client"""
        self.client = None
        self.db = None
        self.collection = None
        self._last_connection_attempt = 0
        self._connection_cooldown = 5  # seconds between reconnection attempts
        
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
        if self.client is None:
            return False
        try:
            self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.warning(f"Connection validation failed: {e}")
            return False
    
    def _close_connection(self):
        """Safely close the database connection"""
        if self.client is not None:
            try:
                self.client.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self.client = None
                self.db = None
                self.collection = None
    
    def _get_connection(self):
        """Get database connection with retry logic and cooldown"""
        current_time = time.time()
        if self._last_connection_attempt > 0:
            time_since_last = current_time - self._last_connection_attempt
            if time_since_last < self._connection_cooldown and not self._is_connection_valid():
                logger.debug(f"Connection cooldown active ({time_since_last:.1f}s / {self._connection_cooldown}s)")
        
        if self._is_connection_valid():
            return self.client
        
        self._close_connection()
        
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                self._last_connection_attempt = time.time()
                logger.info(f"Connecting to MongoDB (attempt {attempt + 1}/{self.MAX_RETRIES})...")
                
                self.client = MongoClient(
                    config.MONGODB_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000
                )
                
                # Test connection
                self.client.admin.command('ping')
                
                self.db = self.client[config.MONGODB_DATABASE]
                self.collection = self.db['user_memories']
                
                # Create index on user_id
                self.collection.create_index("user_id", unique=True)
                
                logger.info("Database connection established successfully")
                return self.client
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                last_error = e
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error connecting to database: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
        
        logger.error(f"Failed to connect to MongoDB after {self.MAX_RETRIES} attempts")
        raise ConnectionError(
            f"Cannot connect to MongoDB at {config.MONGODB_URI} "
            f"after {self.MAX_RETRIES} attempts. Last error: {last_error}\n\n"
            f"Troubleshooting:\n"
            f"1. Check if MongoDB is running: docker ps | grep mongodb\n"
            f"2. If not running: docker compose up -d mongodb\n"
            f"3. Check credentials in .env file"
        )
    
    def _execute_with_retry(self, operation, *args, **kwargs):
        """Execute a database operation with automatic reconnection on failure"""
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                self._get_connection()
                return operation(*args, **kwargs)
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                last_error = e
                logger.warning(f"Database operation failed (attempt {attempt + 1}): {e}")
                self.client = None
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
        system_prompt = """You are a memory extraction system. Extract ALL personal information from user messages. Be thorough - extract every piece of personal data mentioned.

IMPORTANT RULES:
1. Extract EVERYTHING - don't skip any personal information
2. Use specific field names when possible (favorite_color, not likes)
3. Extract multiple fields from a single sentence when applicable
4. Users can have MULTIPLE jobs, roles, companies simultaneously (full-time + part-time, freelance, etc.)

FIELD CATEGORIES (use these exact field names):
IDENTITY: name, nickname, age, birthday, birth_year, gender, nationality, ethnicity, email, phone
LOCATION: location, city, country, hometown, timezone, address

WORK (supports multiple jobs - use jobs[] array for multiple positions):
- For single job: role, job_title, company, employer, industry, salary_range, work_schedule
- For multiple jobs: jobs[] array with objects like {"company": "X", "role": "Y", "type": "full-time/part-time/freelance", "salary": "Z"}
- General work info: experience_years, education, university, degree, graduation_year, career_goals[]

SKILLS: skills[], programming_languages[], tools[], certifications[], expertise[]
PREFERENCES: likes[], dislikes[], hobbies[], interests[]
FAVORITES: favorite_color, favorite_food, favorite_foods[], favorite_music, favorite_genre, favorite_movie, favorite_movies[], favorite_book, favorite_books[], favorite_game, favorite_games[], favorite_sport, favorite_sports[], favorite_animal, favorite_place
LIFESTYLE: diet, exercise_routine, sleep_schedule, work_style, communication_style, morning_person
RELATIONSHIPS: family[], pets[], pet_name, relationship_status, partner_name, spouse_name, children[], children_names[]
LANGUAGES: languages[], native_language, learning_languages[]
HEALTH: allergies[], health_conditions[], blood_type, height, weight
PERSONALITY: personality_type, personality_traits[], values[], life_goals[], fears[], strengths[], weaknesses[]
POSSESSIONS: car, vehicle, phone_model, computer
SOCIAL: social_media[], website, blog

MULTIPLE JOBS EXAMPLES:
- "I work at Google full-time and do freelance on weekends" → 
  {"jobs": [{"company": "Google", "type": "full-time"}, {"type": "freelance"}]}
  
- "I'm a developer at Microsoft and also teach part-time at university" →
  {"jobs": [{"company": "Microsoft", "role": "developer", "type": "full-time"}, {"employer": "university", "role": "teacher", "type": "part-time"}]}

- "My full-time salary is 100k and I make 50k from consulting" →
  {"jobs": [{"type": "full-time", "salary": "100k"}, {"type": "consulting", "salary": "50k"}]}
OTHER: habits[], routines[], memorable_facts[], achievements[], travel_history[], bucket_list[], fun_facts[]

CRITICAL UPDATE RULES:

1. CONTEXT-AWARE EXTRACTION:
   When user mentions a change, extract ALL related information and mark what should be removed.
   
   Example 1 - Job Change:
   Current: {"company": "Google", "role": "Developer", "location": "Mountain View"}
   Message: "I now work at Microsoft"
   Extract: {"company": "Microsoft", "clear_work_context": true}
   → This signals that old work-related fields (role, location) may be outdated
   
   Example 2 - Complete Replacement:
   Current: {"skills": ["Python", "Java", "React"]}
   Message: "My skills are TypeScript and Go"
   Extract: {"replace_skills": ["TypeScript", "Go"]}
   
   Example 3 - Relationship Change:
   Current: {"relationship_status": "married", "partner_name": "Sarah"}
   Message: "I'm single now"
   Extract: {"relationship_status": "single", "remove_partner_name": true}

2. OPERATION TYPES:

   a) NORMAL UPDATE (default for single values):
      {"age": 29} - replaces old age
      {"company": "Microsoft"} - replaces old company
   
   b) ADD TO LIST (use when adding to existing):
      {"skills": ["React"]} - adds React to existing skills
      {"likes": ["pizza"]} - adds pizza to existing likes
   
   c) REPLACE ENTIRE LIST (use "replace_" prefix):
      {"replace_skills": ["Python", "Java"]} - completely replaces skills list
      {"replace_hobbies": ["reading"]} - completely replaces hobbies
   
   d) REMOVE (use "remove_" prefix):
      {"remove_skills": ["Java"]} - removes Java from skills
      {"remove_likes": ["pizza"]} - removes pizza from likes
      {"remove_partner_name": true} - deletes partner_name field
   
   e) CLEAR CONTEXT (use "clear_" prefix for related fields):
      {"clear_work_context": true} - signals work-related fields may be outdated
      {"clear_relationship_context": true} - signals relationship fields may be outdated

3. DETECTING INTENT:

   REPLACEMENT signals:
   - "now", "currently", "these days"
   - "My X is/are..." (definitive statement)
   - "I only...", "just..."
   
   ADDITION signals:
   - "also", "additionally", "too", "as well"
   - "I learned...", "I started..."
   
   REMOVAL signals:
   - "no longer", "not anymore", "don't...anymore"
   - "forgot", "stopped", "quit"
   - "I'm single" (when was in relationship)

4. RELATIONSHIP AWARENESS:

   When these fields change, consider related fields:
   - company changes → role, location might be outdated
   - relationship_status changes → partner_name, children might need update
   - location changes → timezone, address might need update
   - age changes → birthday might need update

EXAMPLES:

Input: "I'm 29 now"
Current: {"age": 28, "birthday": "March 15"}
Output: {"age": 29}

Input: "I work at Microsoft now"
Current: {"company": "Google", "role": "Developer", "location": "Mountain View"}
Output: {"company": "Microsoft"}
Note: Don't remove role/location unless explicitly stated

Input: "I'm a Product Manager at Microsoft"
Current: {"company": "Google", "role": "Developer"}
Output: {"company": "Microsoft", "role": "Product Manager"}

Input: "My skills are Python, Java, and TypeScript"
Current: {"skills": ["React", "Node.js"]}
Output: {"replace_skills": ["Python", "Java", "TypeScript"]}

Input: "I also know React"
Current: {"skills": ["Python", "Java"]}
Output: {"skills": ["React"]}

Input: "I don't like pizza anymore"
Current: {"likes": ["pizza", "hiking"]}
Output: {"remove_likes": ["pizza"]}

Input: "I'm single now"
Current: {"relationship_status": "married", "partner_name": "Sarah"}
Output: {"relationship_status": "single", "remove_partner_name": true}

Input: "I like tomatoes"
Current: {"dislikes": ["tomatoes"]}
Output: {"likes": ["tomatoes"], "remove_dislikes": ["tomatoes"]}

IMPORTANT: 
- Extract ALL personal information mentioned - be thorough, don't skip anything
- Use specific field names (favorite_color instead of putting color in likes[])
- Extract multiple fields from compound sentences
- For single values (age, name, company), just provide the new value
- Return {} ONLY if the message contains absolutely no personal information
- Extract BOTH explicit AND implied information (e.g., "I work in accounting" implies department=accounting AND possibly role=accountant)
- USE CURRENT MEMORIES to understand context (e.g., if user said "I work at Google" before and now says "I got promoted", infer company is still Google)

Return valid JSON only."""

        user_prompt = f"""CURRENT USER MEMORIES (use this context to understand the new message):
{json.dumps(current_memories, indent=2) if current_memories else "{}"}

NEW MESSAGE: "{message}"

TASK: Analyze this message using the user's existing memories as context, then extract updates.

CONTEXT-AWARE EXTRACTION RULES:
1. Use existing memories to understand pronouns and references
   - If user says "I got a raise" and memories show company=Google, they still work at Google
   - If user says "my dog is sick" and memories show pet_name=Max, the dog is Max
   
2. Detect updates to existing information
   - "I moved to Seattle" should update location if different from current
   - "I'm 30 now" should update age
   - "I switched to TypeScript" may replace or add to programming_languages
   
3. Detect removals or changes
   - "I quit my job" → remove company, role
   - "I don't like pizza anymore" → remove from likes
   - "I'm single now" → update relationship_status, remove partner_name

4. Extract new information not in memories
   - Any personal facts, preferences, skills mentioned
   
5. Infer related information
   - "I use React daily" → skills: React, tools: React, expertise: React

Return ONLY the JSON updates (new values, remove_ prefixes for deletions, replace_ prefixes for full replacements).

JSON OUTPUT:"""

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
            
            # Validate and normalize removal/replacement operations
            for key in list(updates.keys()):
                if key.startswith("remove_"):
                    if not isinstance(updates[key], list) and updates[key] not in [True, ""]:
                        logger.warning(f"Removal value for {key} is not a list or boolean, converting: {updates[key]}")
                        updates[key] = [updates[key]] if updates[key] else []
                elif key.startswith("replace_"):
                    # Ensure replace operations are properly formatted
                    if not isinstance(updates[key], (list, str, int, float)):
                        logger.warning(f"Replace value for {key} has unexpected type: {type(updates[key])}")
            
            # Track changes for reporting
            changes = []
            for key, value in updates.items():
                if key.startswith("remove_"):
                    field_name = key[7:]
                    changes.append({
                        "field": field_name,
                        "value": value,
                        "event": "REMOVE"
                    })
                elif key.startswith("replace_"):
                    field_name = key[8:]
                    changes.append({
                        "field": field_name,
                        "value": value,
                        "event": "REPLACE"
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
        
        Supports three types of operations:
        1. Normal updates: Add to arrays, replace strings
        2. Removals: "remove_" prefix removes items
        3. Replacements: "replace_" prefix completely replaces arrays
        
        Conflict resolution:
        - If item added to "likes", remove it from "dislikes"
        - If item added to "dislikes", remove it from "likes"
        """
        merged = current.copy()
        
        conflict_pairs = [
            ("likes", "dislikes"),
            ("dislikes", "likes"),
        ]
        
        def normalize_item(item):
            return str(item).lower().strip()
        
        # Separate operations by type
        removals_to_process = {}
        replacements_to_process = {}
        normal_updates = {}
        
        for key, value in updates.items():
            if key.startswith("remove_"):
                field_name = key[7:]  # Remove "remove_" prefix
                if isinstance(value, list):
                    removals_to_process[field_name] = value
                elif value is True or value == "":
                    # Handle {"remove_company": true} or {"company": ""}
                    if field_name in merged:
                        del merged[field_name]
                        logger.info(f"Deleted field: {field_name}")
            elif key.startswith("replace_"):
                field_name = key[8:]  # Remove "replace_" prefix
                replacements_to_process[field_name] = value
            else:
                normal_updates[key] = value
        
        # Process removals first
        for field_name, items_to_remove in removals_to_process.items():
            logger.info(f"Processing removal: {field_name} -> {items_to_remove}")
            if field_name in merged:
                if isinstance(merged[field_name], list):
                    original_count = len(merged[field_name])
                    items_to_remove_normalized = {normalize_item(item) for item in items_to_remove}
                    
                    merged[field_name] = [
                        item for item in merged[field_name]
                        if normalize_item(item) not in items_to_remove_normalized
                    ]
                    
                    removed_count = original_count - len(merged[field_name])
                    logger.info(f"Removed {removed_count} items from {field_name}. Remaining: {merged[field_name]}")
                    
                    if not merged[field_name]:
                        del merged[field_name]
                        logger.info(f"Deleted empty {field_name} field")
                else:
                    # For non-list fields, check if value matches
                    current_value = merged[field_name]
                    current_value_normalized = normalize_item(current_value)
                    items_to_remove_normalized = {normalize_item(item) for item in items_to_remove}
                    
                    if current_value_normalized in items_to_remove_normalized:
                        del merged[field_name]
                        logger.info(f"Deleted {field_name} field (value matched: {current_value})")
            else:
                logger.debug(f"Field {field_name} not found for removal")
        
        # Process replacements (complete overwrites)
        for field_name, new_value in replacements_to_process.items():
            logger.info(f"Processing replacement: {field_name} -> {new_value}")
            if isinstance(new_value, list):
                # Deduplicate the replacement list
                seen_normalized = set()
                merged[field_name] = []
                for item in new_value:
                    item_normalized = normalize_item(item)
                    if item_normalized not in seen_normalized:
                        seen_normalized.add(item_normalized)
                        merged[field_name].append(item)
                logger.info(f"Replaced {field_name} with: {merged[field_name]}")
            else:
                merged[field_name] = new_value
                logger.info(f"Replaced {field_name} with: {new_value}")
        
        # Handle conflict resolution for normal updates
        for key, value in normal_updates.items():
            if isinstance(value, list) and value:
                for field, opposite_field in conflict_pairs:
                    if key == field and opposite_field in merged:
                        if isinstance(merged[opposite_field], list):
                            new_values_normalized = {normalize_item(v) for v in value}
                            original_count = len(merged[opposite_field])
                            merged[opposite_field] = [
                                item for item in merged[opposite_field]
                                if normalize_item(item) not in new_values_normalized
                            ]
                            if len(merged[opposite_field]) < original_count:
                                logger.info(f"Removed conflicting items from {opposite_field}")
                            if not merged[opposite_field]:
                                del merged[opposite_field]
                                logger.info(f"Deleted empty {opposite_field} field")
        
        # Process normal updates
        for key, value in normal_updates.items():
            if isinstance(value, list):
                if key in merged and isinstance(merged[key], list):
                    # Append unique items to existing list
                    existing_normalized = {normalize_item(item) for item in merged[key]}
                    added_count = 0
                    for new_item in value:
                        if normalize_item(new_item) not in existing_normalized:
                            merged[key].append(new_item)
                            existing_normalized.add(normalize_item(new_item))
                            added_count += 1
                    if added_count > 0:
                        logger.info(f"Added {added_count} items to {key}: {value}")
                else:
                    # Create new list with deduplication
                    seen_normalized = set()
                    merged[key] = []
                    for item in value:
                        item_normalized = normalize_item(item)
                        if item_normalized not in seen_normalized:
                            seen_normalized.add(item_normalized)
                            merged[key].append(item)
                    logger.info(f"Created new {key}: {merged[key]}")
            else:
                # For non-list values, always replace
                if key in merged and merged[key] != value:
                    logger.info(f"Replaced {key}: {merged[key]} -> {value}")
                else:
                    logger.info(f"Set {key}: {value}")
                merged[key] = value
        
        return merged
    
    def _save_memories(self, user_id: str, memories: Dict[str, Any]):
        """Save memories to MongoDB"""
        def _do_save():
            logger.debug(f"Saving memories for {user_id}: {memories}")
            self._get_connection()
            
            self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "memories": memories,
                        "updated_at": time.time()
                    },
                    "$setOnInsert": {
                        "created_at": time.time()
                    }
                },
                upsert=True
            )
            logger.info(f"Successfully saved memories to database for user {user_id}")
        
        self._execute_with_retry(_do_save)
    
    def get_user_memories(self, user_id: str) -> Dict[str, Any]:
        """
        Get all memories for a user.
        
        Returns:
            Dictionary of memories (empty dict if no memories)
        """
        def _do_get():
            self._get_connection()
            result = self.collection.find_one({"user_id": user_id})
            
            if result and "memories" in result:
                return result["memories"]
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
            self._get_connection()
            self.collection.delete_one({"user_id": user_id})
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
