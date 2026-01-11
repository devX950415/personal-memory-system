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

## API Endpoints

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

### Get Memories (Formatted)
```
GET /users/{user_id}/memories
```

**Response:**
```json
[
  {"id": "user123_name", "memory": "name: John", "user_id": "user123", "created_at": "...", "updated_at": "..."},
  {"id": "user123_likes", "memory": "likes: Python", "user_id": "user123", "created_at": "...", "updated_at": "..."}
]
```

### Get Memories (Raw JSON)
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

### Delete All Memories
```
DELETE /users/{user_id}/memories
```

### Delete Single Memory
```
DELETE /memories/{memory_id}
```

### Health Check
```
GET /health
```

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

```python
import requests

API_URL = "http://localhost:8888"

# Store user info
response = requests.post(f"{API_URL}/messages", json={
    "user_id": "user123",
    "message": "I'm Alice, a frontend developer who loves React"
})
print(response.json())

# Get memories
response = requests.get(f"{API_URL}/users/user123/memories/raw")
memories = response.json()["memories"]
# {"name": "Alice", "role": "frontend developer", "likes": ["React"]}
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
