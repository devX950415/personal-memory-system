# Schema Control in PersonalMem

## Overview: Who Controls What?

The schema in PersonalMem is controlled by **3 main components**:

```
┌─────────────────────────────────────────────────────────────┐
│                    SCHEMA CONTROL FLOW                      │
└─────────────────────────────────────────────────────────────┘

1. MongoDB (Minimal)     →  Collection + Index only
2. LLM Prompt (Primary)  →  Field names and types
3. Merge Logic (Rules)   →  How fields combine
```

---

## 1. MongoDB Collection Definition (Minimal Schema)

**Location:** `memory_service.py` → `_get_connection()` method (lines ~105-111)

```python
self.db = self.client[config.MONGODB_DATABASE]
self.collection = self.db['user_memories']

# Create index on user_id
self.collection.create_index("user_id", unique=True)
```

**What it defines:**
- ✅ Collection name: `user_memories`
- ✅ Index: `user_id` (unique)
- ❌ NO field definitions
- ❌ NO data types
- ❌ NO required fields

**This is NOT a traditional schema!** MongoDB is schema-less, so this just creates the collection and ensures `user_id` is unique.

---

## 2. LLM Prompt (Primary Schema Definition) ⭐

**Location:** `memory_service.py` → `_extract_structured_memories()` method (lines ~207-237)

```python
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
"""
```

**What it defines:**
- ✅ **Field names** (name, age, skills, likes, etc.)
- ✅ **Data types** (strings vs arrays)
- ✅ **Categories** (IDENTITY, WORK, PREFERENCES, etc.)
- ✅ **Extraction rules** (what to extract, what to skip)
- ✅ **Special operations** (remove_ prefix for deletions)

**This is the REAL schema definition!** The LLM uses this prompt to decide:
- What fields to create
- What data type to use
- When to create new fields
- How to structure the data

### How to Modify the Schema

**Want to add a new field category?** Edit this prompt!

```python
# Add this line to the prompt:
SOCIAL_MEDIA: twitter_handle, linkedin_url, github_username, instagram_handle
```

**Want to change field names?** Edit the prompt!

```python
# Change from:
WORK: role, company, skills[]

# To:
WORK: job_title, employer, technical_skills[]
```

**Want to add validation rules?** Edit the prompt!

```python
# Add to RULES section:
- Age must be a number between 0-150
- Email must be valid format
- Skills must be capitalized
```

---

## 3. Merge Logic (Schema Behavior)

**Location:** `memory_service.py` → `_merge_memories()` method (lines ~303-410)

```python
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
```

**What it defines:**
- ✅ **Array behavior**: Append unique items, no duplicates
- ✅ **String behavior**: Replace old value with new
- ✅ **Conflict resolution**: likes/dislikes are mutually exclusive
- ✅ **Removal logic**: `remove_` prefix removes items from arrays
- ✅ **Normalization**: Case-insensitive comparison

### Key Merge Rules

**Arrays (lists):**
```python
# Current
{"skills": ["Python"]}

# New
{"skills": ["JavaScript"]}

# Result (append unique)
{"skills": ["Python", "JavaScript"]}
```

**Strings:**
```python
# Current
{"name": "John"}

# New
{"name": "John Smith"}

# Result (replace)
{"name": "John Smith"}
```

**Conflicts:**
```python
# Current
{"likes": ["pizza"], "dislikes": ["tomatoes"]}

# New
{"likes": ["tomatoes"]}

# Result (auto-resolve)
{"likes": ["pizza", "tomatoes"], "dislikes": []}
```

**Removals:**
```python
# Current
{"skills": ["Python", "Java", "React"]}

# New
{"remove_skills": ["Java"]}

# Result
{"skills": ["Python", "React"]}
```

### How to Modify Merge Behavior

**Add new conflict pairs:**
```python
conflict_pairs = [
    ("likes", "dislikes"),
    ("dislikes", "likes"),
    ("strengths", "weaknesses"),  # Add this
    ("weaknesses", "strengths"),  # Add this
]
```

**Change array behavior to replace instead of append:**
```python
# Find this code (around line 390):
if isinstance(value, list):
    if key in merged and isinstance(merged[key], list):
        # CURRENT: Append unique items
        existing_normalized = {normalize_item(item) for item in merged[key]}
        for new_item in value:
            if normalize_item(new_item) not in existing_normalized:
                merged[key].append(new_item)
    
    # CHANGE TO: Replace entire array
    merged[key] = value
```

---

## 4. Save Operation (No Schema Enforcement)

**Location:** `memory_service.py` → `_save_memories()` method (lines ~412-430)

```python
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
```

**What it does:**
- ✅ Saves ANY JSON structure (no validation)
- ✅ Upserts (creates if not exists, updates if exists)
- ✅ Adds timestamps automatically
- ❌ NO schema validation
- ❌ NO type checking
- ❌ NO required field enforcement

---

## Summary: Schema Control Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│  Component          │  Controls              │  Flexibility │
├─────────────────────────────────────────────────────────────┤
│  1. MongoDB         │  Collection + Index    │  Fixed       │
│  2. LLM Prompt ⭐   │  Field names & types   │  Editable    │
│  3. Merge Logic     │  Field behavior        │  Editable    │
│  4. Save Operation  │  No validation         │  Accepts all │
└─────────────────────────────────────────────────────────────┘
```

### To Change the Schema:

1. **Add/remove field categories** → Edit LLM prompt (lines 207-237)
2. **Change field names** → Edit LLM prompt
3. **Modify merge behavior** → Edit `_merge_memories()` (lines 303-410)
4. **Add conflict resolution** → Edit `conflict_pairs` in `_merge_memories()`
5. **Change data types** → Edit LLM prompt rules

### The schema is primarily defined by the LLM prompt, not the database!

This is a **prompt-driven schema** system, which makes it extremely flexible and easy to modify without database migrations.
