# PersonalMem

Personal memory management API that extracts and stores user information from messages using LLM. Built for chatbot backends.

## Tech Stack

- **FastAPI** - REST API
- **MongoDB** - Storage
- **Azure OpenAI / OpenAI** - LLM for extraction

## Quick Start

```bash
# 1. Start MongoDB
docker compose up -d mongodb

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

### Overview

| Endpoint | Why It's Needed |
|----------|-----------------|
| `POST /messages` | Automatically extracts and stores personal information from user messages so your chatbot can remember users across conversations. |
| `GET /users/{user_id}/context/text` | Provides formatted user context to inject into your chatbot's system prompt for personalized responses. |
| `GET /users/{user_id}/memories/raw` | Returns structured JSON data for displaying user profiles or integrating with other systems. |
| `POST /users/{user_id}/memories/batch` | Allows you to set or update user memories directly with structured data, bypassing LLM extraction (instant and free). |
| `DELETE /users/{user_id}/memories` | Enables users to delete their data for GDPR compliance and privacy. |

---

### 1. POST /messages

**Why:** Automatically extracts and stores personal information from user messages so your chatbot can remember users across conversations.

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
  "extracted_memories": [
    {"field": "name", "value": "John", "event": "ADD"},
    {"field": "likes", "value": ["Python"], "event": "ADD"}
  ],
  "response_time_ms": 850
}
```

---

### 2. GET /users/{user_id}/context/text

**Why:** Provides formatted user context to inject into your chatbot's system prompt for personalized responses.

**Response:**
```json
{
  "user_id": "user123",
  "context": "User Information:\n- name: John\n- likes: Python",
  "has_memories": true
}
```

**Usage:**
```python
response = requests.get(f"{API_URL}/users/{user_id}/context/text")
context = response.json()["context"]
system_prompt = f"You are a helpful assistant.\n\n{context}"
```

---

### 3. GET /users/{user_id}/memories/raw

**Why:** Returns structured JSON data for displaying user profiles or integrating with other systems.

**Response:**
```json
{
  "user_id": "user123",
  "memories": {
    "name": "John",
    "likes": ["Python"],
    "age": 28
  }
}
```

---

### 4. POST /users/{user_id}/memories/batch

**Why:** Allows you to set or update user memories directly with structured data, bypassing LLM extraction (instant and free).

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
  "updated_fields": ["name", "skills"],
  "total_fields": 5
}
```

---

### 5. DELETE /users/{user_id}/memories

**Why:** Enables users to delete their data for GDPR compliance and privacy.

**Response:**
```json
{
  "message": "All memories deleted for user user123"
}
```

## Chatbot Integration Example

```python
import requests
import openai

MEMORY_API = "http://localhost:8888"

def chat_with_memory(user_id: str, user_message: str):
    # 1. Extract and store memories
    requests.post(f"{MEMORY_API}/messages", json={
        "user_id": user_id,
        "message": user_message
    })
    
    # 2. Get user context
    response = requests.get(f"{MEMORY_API}/users/{user_id}/context/text")
    user_context = response.json()["context"]
    
    # 3. Build chatbot prompt with context
    system_prompt = f"You are a helpful assistant.\n\n{user_context}"
    
    # 4. Call your chatbot
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    
    return response.choices[0].message.content
```

## What Gets Extracted

The system extracts comprehensive personal information:

**Identity:** name, age, gender, nationality
**Work:** role, company, skills, education
**Preferences:** likes, dislikes, hobbies, interests, favorites
**Lifestyle:** diet, exercise, work_style
**Relationships:** family, pets
**Languages:** spoken, native, learning
**Other:** habits, goals, personality traits

## Environment Variables

```env
# MongoDB
MONGODB_URI=mongodb://admin:admin123@localhost:27017/
MONGODB_DATABASE=personalmem

# Azure OpenAI (recommended)
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_MODEL=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-04-01-preview

# Or OpenAI
OPENAI_API_KEY=sk-your-key
```

## Troubleshooting

### Database Connection Issues

The system automatically connects to MongoDB. If problems persist:

```bash
# Reset MongoDB
docker compose down -v
docker compose up -d mongodb

# Wait 5 seconds, then restart API
uvicorn api:app --reload --host 0.0.0.0 --port 8888
```

### Common Issues

**"Cannot connect to MongoDB"**
- Check if MongoDB is running: `docker ps | grep mongodb`
- If not running: `docker compose up -d mongodb`

**"Authentication failed"**
- Check `.env` credentials (default: admin/admin123)

**"connection refused"**
```bash
docker compose up -d mongodb
```

## Project Structure

```
PersonalMem/
├── api.py              # FastAPI endpoints
├── app.py              # Application logic
├── memory_service.py   # Memory extraction & storage
├── config.py           # Configuration
├── docker-compose.yml  # MongoDB setup
├── requirements.txt    # Dependencies
└── frontend/           # Test UI
    ├── index.html
    ├── app.js
    └── styles.css
```

## License

MIT
