# PersonalMem Data Schema

## Overview

PersonalMem uses a **schema-less, flexible JSON structure** in MongoDB. Each user has ONE document that contains ALL their personal information.

---

## MongoDB Collection: `user_memories`

### Collection Structure

```
Database: personalmem
Collection: user_memories
Index: user_id (unique)
```

---

## Document Schema

Each document represents one user's complete memory profile:

```json
{
  "_id": ObjectId("..."),           // MongoDB auto-generated ID
  "user_id": "user123",             // Unique user identifier (indexed)
  "memories": {                     // Flexible JSON object with user info
    // IDENTITY
    "name": "John Smith",
    "nickname": "Johnny",
    "age": 28,
    "birthday": "March 15",
    "gender": "male",
    
    // WORK
    "role": "Senior Developer",
    "company": "Google",
    "skills": ["Python", "JavaScript", "Docker"],
    "experience_years": 5,
    
    // PREFERENCES
    "likes": ["pizza", "hiking", "coding"],
    "dislikes": ["tomatoes", "meetings"],
    "hobbies": ["photography", "gaming"],
    
    // RELATIONSHIPS
    "family": ["wife Sarah", "son aged 3"],
    "pets": ["dog named Max"],
    
    // LANGUAGES
    "languages": ["English", "Spanish"],
    "learning_languages": ["Japanese"],
    
    // LIFESTYLE
    "diet": "vegetarian",
    "allergies": ["nuts", "shellfish"],
    
    // ... any other fields the LLM extracts
  },
  "created_at": 1705176234.567,    // Unix timestamp
  "updated_at": 1705176890.123     // Unix timestamp
}
```

---

## Key Characteristics

### 1. **Schema-less Design**
- No fixed schema - fields are added dynamically
- LLM decides what fields to create based on user messages
- New fields can be added at any time without migration

### 2. **Flexible Data Types**
- **Strings**: `"name": "John"`, `"role": "developer"`
- **Numbers**: `"age": 28`, `"experience_years": 5`
- **Arrays**: `"skills": ["Python", "Java"]`, `"likes": ["pizza"]`
- **Mixed**: Any combination based on context

### 3. **One Document Per User**
- Each user has exactly ONE document
- All updates merge into the existing document
- No separate tables or collections for different data types

---

## Common Field Categories

The LLM extracts information into these categories (but can create new ones):

### Identity
```json
{
  "name": "string",
  "nickname": "string",
  "age": number,
  "birthday": "string",
  "gender": "string",
  "nationality": "string",
  "ethnicity": "string"
}
```

### Work & Career
```json
{
  "role": "string",
  "company": "string",
  "industry": "string",
  "experience_years": number,
  "stack": "string",
  "skills": ["array"],
  "certifications": ["array"],
  "education": "string",
  "career_goals": ["array"]
}
```

### Preferences
```json
{
  "likes": ["array"],
  "dislikes": ["array"],
  "hobbies": ["array"],
  "interests": ["array"],
  "favorite_foods": ["array"],
  "favorite_music": ["array"],
  "favorite_movies": ["array"],
  "favorite_books": ["array"]
}
```

### Lifestyle
```json
{
  "diet": "string",
  "exercise": "string",
  "sleep_schedule": "string",
  "work_style": "string",
  "communication_style": "string",
  "morning_person": "boolean/string"
}
```

### Relationships
```json
{
  "family": ["array"],
  "pets": ["array"],
  "relationship_status": "string",
  "partner_name": "string",
  "children": ["array"]
}
```

### Languages
```json
{
  "languages": ["array"],
  "native_language": "string",
  "learning_languages": ["array"]
}
```

### Health
```json
{
  "allergies": ["array"],
  "health_conditions": ["array"],
  "disabilities": ["array"]
}
```

### Personality
```json
{
  "personality_traits": ["array"],
  "values": ["array"],
  "life_goals": ["array"],
  "fears": ["array"],
  "strengths": ["array"],
  "weaknesses": ["array"]
}
```

---

## Data Operations

### 1. **Create/Update (Upsert)**

When a user sends a message, the system:
1. Extracts new information using LLM
2. Merges with existing memories
3. Upserts the document

```javascript
// MongoDB operation
db.user_memories.updateOne(
  { user_id: "user123" },
  {
    $set: {
      memories: { /* merged data */ },
      updated_at: timestamp
    },
    $setOnInsert: {
      created_at: timestamp
    }
  },
  { upsert: true }
)
```

### 2. **Read**

```javascript
// Get all memories for a user
db.user_memories.findOne({ user_id: "user123" })

// Returns:
{
  "_id": ObjectId("..."),
  "user_id": "user123",
  "memories": { /* all user data */ },
  "created_at": 1705176234.567,
  "updated_at": 1705176890.123
}
```

### 3. **Delete**

```javascript
// Delete all memories for a user
db.user_memories.deleteOne({ user_id: "user123" })
```

---

## Memory Merge Logic

### Adding to Arrays
```
Current: { "skills": ["Python"] }
New:     { "skills": ["JavaScript"] }
Result:  { "skills": ["Python", "JavaScript"] }
```

### Replacing Strings
```
Current: { "name": "John" }
New:     { "name": "John Smith" }
Result:  { "name": "John Smith" }
```

### Removing from Arrays
```
Current: { "skills": ["Python", "Java", "React"] }
Message: "I forgot Java"
LLM:     { "remove_skills": ["Java"] }
Result:  { "skills": ["Python", "React"] }
```

### Conflict Resolution
```
Current: { "likes": ["pizza"], "dislikes": ["tomatoes"] }
Message: "Actually, I like tomatoes now"
LLM:     { "likes": ["tomatoes"] }
Result:  { "likes": ["pizza", "tomatoes"], "dislikes": [] }
         // "tomatoes" removed from dislikes automatically
```

---

## Example: Complete User Document

```json
{
  "_id": ObjectId("65a1b2c3d4e5f6789abcdef0"),
  "user_id": "alice_2024",
  "memories": {
    "name": "Alice Johnson",
    "age": 32,
    "role": "Senior Software Engineer",
    "company": "Microsoft",
    "skills": ["Python", "TypeScript", "Kubernetes", "AWS"],
    "experience_years": 8,
    "likes": ["coffee", "hiking", "sci-fi movies"],
    "dislikes": ["meetings", "cold weather"],
    "hobbies": ["photography", "rock climbing"],
    "family": ["husband Tom", "daughter Emma aged 5"],
    "pets": ["cat named Whiskers"],
    "languages": ["English", "French"],
    "learning_languages": ["Mandarin"],
    "diet": "pescatarian",
    "allergies": ["peanuts"],
    "location": "Seattle, WA",
    "timezone": "PST",
    "work_style": "remote-first",
    "personality_traits": ["introverted", "analytical", "creative"],
    "life_goals": ["start a tech company", "travel to Japan"]
  },
  "created_at": 1705176234.567,
  "updated_at": 1705180456.789
}
```

---

## Advantages of This Schema

1. **Flexibility**: No migrations needed when adding new field types
2. **Simplicity**: One document per user, easy to understand
3. **Performance**: Single document read/write operations
4. **Natural**: Matches how LLMs think about user information
5. **Scalable**: MongoDB handles JSON documents efficiently

---

## Querying Examples

### Get all memories
```javascript
db.user_memories.findOne({ user_id: "alice_2024" })
```

### Check if user exists
```javascript
db.user_memories.countDocuments({ user_id: "alice_2024" })
```

### Find users with specific skill
```javascript
db.user_memories.find({ "memories.skills": "Python" })
```

### Find users in a location
```javascript
db.user_memories.find({ "memories.location": /Seattle/i })
```

### Get recently updated users
```javascript
db.user_memories.find().sort({ updated_at: -1 }).limit(10)
```

---

## Schema Evolution

The schema evolves naturally:
- LLM extracts new field types as users share information
- No database migrations required
- Old documents work alongside new ones
- Fields can be added/removed per user independently

This makes the system extremely flexible and future-proof!
