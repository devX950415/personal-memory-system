# PersonalMem

Personal memory management API that extracts and stores user information from messages using LLM. Built for chatbot backends that need to remember user preferences, context, and personal details across conversations.

## Features

- **Automatic Memory Extraction** - LLM analyzes messages and extracts personal information
- **Flexible Schema** - Schema-less MongoDB storage adapts to any user data
- **Smart Merging** - Intelligently combines new info with existing memories
- **Fast API** - RESTful endpoints for easy integration
- **Context Ready** - Formatted output for chatbot prompts
- **GDPR Compliant** - User data deletion support

## Tech Stack

- **FastAPI** - REST API framework
- **MongoDB** - Flexible document storage
- **Azure OpenAI / OpenAI** - LLM for memory extraction
- **Docker** - Containerized MongoDB deployment

## Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Create .env file
cp env_example.txt .env
# Edit .env and add your AZURE_OPENAI_API_KEY

# 2. Build and run
docker compose up -d

# 3. Access
# API: http://localhost:8888/docs
# Frontend: http://localhost:8888
```

### Option 2: Local Development

```bash
# 1. Start MongoDB
docker compose up -d

# 2. Configure environment
cp env_example.txt .env
# Edit .env with your Azure OpenAI or OpenAI credentials

# 3. Install dependencies
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4. Run API
uvicorn api:app --reload --host 0.0.0.0 --port 8888
```

**Access:**
- API Documentation: http://localhost:8888/docs
- Test Frontend: http://localhost:8888
- MongoDB: localhost:27017 (admin/admin123)

**Note:** The Docker image includes both the application and MongoDB in a single container. See [DOCKER.md](DOCKER.md) for detailed Docker deployment guide.

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

The LLM automatically extracts and categorizes personal information:

| Category | Fields |
|----------|--------|
| **Identity** | name, nickname, age, birthday, gender, nationality, ethnicity |
| **Location** | location, hometown, timezone, address |
| **Work** | role, company, industry, skills, education, experience_years |
| **Preferences** | likes, dislikes, hobbies, interests, favorite_foods, favorite_music |
| **Lifestyle** | diet, exercise, sleep_schedule, work_style, communication_style |
| **Relationships** | family, pets, relationship_status, partner_name, children |
| **Languages** | languages, native_language, learning_languages |
| **Health** | allergies, health_conditions, disabilities |
| **Personality** | personality_traits, values, life_goals, fears, strengths |
| **Other** | habits, routines, achievements, travel_history, bucket_list |

The schema is flexible - new fields are created automatically as needed!

## Configuration

### Environment Variables

Create a `.env` file with:

```env
# MongoDB Configuration
MONGODB_URI=mongodb://admin:admin123@localhost:27017/
MONGODB_DATABASE=personalmem

# Azure OpenAI (Recommended)
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_MODEL=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-04-01-preview

# OR Regular OpenAI
OPENAI_API_KEY=sk-your-openai-key

# Application Settings
LOG_LEVEL=INFO
```

### MongoDB Connection

The default MongoDB credentials are:
- **Username:** admin
- **Password:** admin123
- **Port:** 27017
- **Database:** personalmem

To change credentials, edit `docker-compose.yml`:
```yaml
environment:
  MONGO_INITDB_ROOT_USERNAME: your_username
  MONGO_INITDB_ROOT_PASSWORD: your_password
```

Then update `MONGODB_URI` in `.env` accordingly.

## Data Schema

PersonalMem uses a **flexible, schema-less design**:

```json
{
  "_id": ObjectId("..."),
  "user_id": "user123",
  "memories": {
    "name": "John Smith",
    "age": 28,
    "role": "Developer",
    "skills": ["Python", "JavaScript"],
    "likes": ["pizza", "hiking"],
    "family": ["wife Sarah", "son aged 3"]
    // ... any other fields
  },
  "created_at": 1705176234.567,
  "updated_at": 1705176890.123
}
```

**Key Features:**
- One document per user
- No fixed schema - fields added dynamically
- Arrays for lists, strings for single values
- Smart merging (arrays append, strings replace)
- Conflict resolution (likes/dislikes are mutually exclusive)

## Troubleshooting

### MongoDB Connection Issues

```bash
# Check if MongoDB is running
docker ps | grep mongodb

# If not running, start it
docker compose up -d

# Reset MongoDB (clears all data)
docker compose down -v
docker compose up -d
```

### Common Issues

| Issue | Solution |
|-------|----------|
| **"Cannot connect to MongoDB"** | Run `docker compose up -d` |
| **"Authentication failed"** | Check `.env` credentials (default: admin/admin123) |
| **"Database connection not available"** | Wait 5-10 seconds for MongoDB to start, then retry |
| **Port 27017 already in use** | Stop other MongoDB instances or change port in `docker-compose.yml` |

### Testing MongoDB Connection

```bash
# Test from command line
docker exec -it personalmem_mongodb mongosh \
  --username admin \
  --password admin123 \
  --authenticationDatabase admin

# Inside mongosh:
use personalmem
db.user_memories.find()
```

### API Not Starting

```bash
# Check Python dependencies
pip install -r requirements.txt

# Check if port 8888 is available
lsof -i :8888  # On Linux/Mac
netstat -ano | findstr :8888  # On Windows

# Run with debug logging
LOG_LEVEL=DEBUG uvicorn api:app --reload --host 0.0.0.0 --port 8888
```

## Project Structure

```
PersonalMem/
├── api.py                 # FastAPI REST endpoints
├── app.py                 # Application logic layer
├── memory_service.py      # LLM extraction & MongoDB storage
├── config.py              # Configuration management
├── docker-compose.yml     # MongoDB container setup
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create from env_example.txt)
├── env_example.txt        # Environment template
└── frontend/              # Test UI
    ├── index.html         # Web interface
    ├── app.js             # Frontend logic
    └── styles.css         # Styling
```

## License

MIT License - feel free to use in your projects!
