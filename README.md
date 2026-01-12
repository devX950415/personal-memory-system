# PersonalMem

A personal memory management API that automatically extracts and stores user information from messages using LLM.

## Overview

PersonalMem analyzes user messages and extracts personal information (name, preferences, skills, etc.) storing them in PostgreSQL. Useful for building personalized AI assistants that remember user context across sessions.

## Tech Stack

- **FastAPI** - REST API
- **PostgreSQL** - Storage (JSONB)
- **Azure OpenAI / OpenAI** - LLM for extraction

## Quick Start

```bash
# 1. Start PostgreSQL
docker compose up -d postgres

# 2. Configure environment
cp env_example.txt .env
# Edit .env with your OpenAI credentials

# 3. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Run API
uvicorn api:app --reload --host 0.0.0.0 --port 8888
```

API docs: http://localhost:8888/docs
Frontend: http://localhost:8888

## API Endpoints

### For Chatbot Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/messages` | POST | Process message and extract memories |
| `/users/{user_id}/context/text` | GET | Get formatted context for chatbot prompt |
| `/users/{user_id}/memories/raw` | GET | Get raw memories as JSON |
| `/users/{user_id}/memories/batch` | POST | Batch update memories programmatically |

### Process Message
```
POST /messages
```
Extracts personal info from message and stores it.

**Request:**
```json
{
  "user_id": "user123",
  "message": "My name is John and I love Python"
}
```

**Response:**
```json
{
  "success": true,
  "memory_context": "User Personal Information:\n- name: John\n- likes: Python",
  "extracted_memories": [
    {"field": "name", "value": "John", "event": "ADD"},
    {"field": "likes", "value": ["Python"], "event": "ADD"}
  ],
  "response_time_ms": 850
}
```

### Get Context for Chatbot
```
GET /users/{user_id}/context/text
```

**Response:**
```json
{
  "user_id": "user123",
  "context": "User Information:\n- name: John\n- likes: Python",
  "has_memories": true
}
```

### Get Raw Memories
```
GET /users/{user_id}/memories/raw
```

**Response:**
```json
{
  "user_id": "user123",
  "memories": {
    "name": "John",
    "likes": ["Python"],
    "role": "developer"
  }
}
```

### Batch Update Memories
```
POST /users/{user_id}/memories/batch
```

**Request:**
```json
{
  "name": "Alice",
  "skills": ["Python", "JavaScript"]
}
```

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "updated_fields": ["name", "skills"],
  "total_fields": 5
}
```

### Other Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/users/{user_id}/memories` | GET | Get all memories (formatted) |
| `/users/{user_id}/memories/search` | GET | Search memories |
| `/users/{user_id}/memories` | DELETE | Delete all memories |
| `/memories/{memory_id}` | DELETE | Delete specific memory |
| `/health` | GET | Health check |

## What Gets Extracted

The system extracts comprehensive personal information:

| Category | Fields |
|----------|--------|
| Identity | name, nickname, age, birthday, gender, nationality |
| Location | location, hometown, timezone |
| Work | role, company, skills, education, experience_years |
| Preferences | likes, dislikes, hobbies, interests, favorites |
| Lifestyle | diet, exercise, work_style |
| Relationships | family, pets, relationship_status |
| Languages | languages, native_language, learning_languages |
| Health | allergies, health_conditions |
| Personality | personality_traits, values, goals |

## Environment Variables

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=personalmem
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Azure OpenAI (recommended)
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_MODEL=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-04-01-preview

# Or OpenAI
OPENAI_API_KEY=sk-your-key
```

## Integration Example

### Basic Integration (Python)

```python
import requests

API_URL = "http://localhost:8888"

# Store user info from chat message
response = requests.post(f"{API_URL}/messages", json={
    "user_id": "user123",
    "message": "I'm Alice, a frontend developer who loves React"
})
result = response.json()
print(f"Extracted: {result['extracted_memories']}")

# Get memories for chatbot context
response = requests.get(f"{API_URL}/users/user123/context/text")
context = response.json()
print(context["context"])
# Output:
# User Information:
# - name: Alice
# - role: frontend developer
# - likes: React
```

### Chatbot Integration

```python
import requests
import openai

MEMORY_API = "http://localhost:8888"

def chat_with_memory(user_id: str, user_message: str):
    # 1. Extract and store memories from user message
    requests.post(f"{MEMORY_API}/messages", json={
        "user_id": user_id,
        "message": user_message
    })
    
    # 2. Get user context for chatbot
    response = requests.get(f"{MEMORY_API}/users/{user_id}/context/text")
    user_context = response.json()["context"]
    
    # 3. Build chatbot prompt with context
    system_prompt = f"""You are a helpful assistant.
    
{user_context}

Use this information to personalize your responses."""
    
    # 4. Call your chatbot
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    
    return response.choices[0].message.content

# Usage
reply = chat_with_memory("user123", "What programming languages do I like?")
print(reply)  # Will reference React from memory
```

### Node.js Integration

```javascript
const axios = require('axios');

const MEMORY_API = 'http://localhost:8888';

async function chatWithMemory(userId, userMessage) {
    // Store memories
    await axios.post(`${MEMORY_API}/messages`, {
        user_id: userId,
        message: userMessage
    });
    
    // Get context
    const { data } = await axios.get(`${MEMORY_API}/users/${userId}/context/text`);
    
    // Use data.context in your chatbot system prompt
    return data.context;
}
```

### Direct Memory Management

```python
# Set memories programmatically
requests.post(f"{API_URL}/users/user123/memories/batch", json={
    "name": "Alice",
    "role": "developer",
    "skills": ["Python", "JavaScript"]
})

# Get raw memories as JSON
response = requests.get(f"{API_URL}/users/user123/memories/raw")
memories = response.json()["memories"]
# {"name": "Alice", "role": "developer", "skills": ["Python", "JavaScript"]}
```

## Troubleshooting

### Database Connection Issues

The system automatically creates the database and handles connection issues. If problems persist:

```bash
# Reset PostgreSQL completely
docker compose down
docker volume rm personalmem_postgres_data
docker compose up -d postgres

# Wait 10 seconds, then restart API
uvicorn api:app --reload --host 0.0.0.0 --port 8888
```

### Common Issues

**"database personalmem does not exist"**
- System auto-creates it on startup
- If error persists, restart PostgreSQL: `docker compose restart postgres`

**"password authentication failed"**
- Check `.env` file has correct credentials
- Default: user=postgres, password=postgres

**"connection refused"**
```bash
docker compose up -d postgres
```

**Container won't start**
```bash
docker compose down
docker volume rm personalmem_postgres_data
docker compose up -d postgres
```

## Project Structure

```
PersonalMem/
├── api.py              # FastAPI endpoints
├── app.py              # Application logic
├── memory_service.py   # Memory extraction & storage
├── config.py           # Configuration
├── docker-compose.yml  # PostgreSQL setup
├── init_db.sql         # Database schema
├── requirements.txt    # Dependencies
└── frontend/           # Test UI
    ├── index.html
    ├── app.js
    └── styles.css
```

## License

MIT
