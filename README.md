# PersonalMem: Personalized User Memory System

A personal memory management system that automatically extracts and stores **long-term personal information** about users from their messages, using LLM-powered extraction and PostgreSQL for persistent storage.

This system is inspired by ChatGPT's **personal memory** feature, built with **PostgreSQL** (JSONB) and **Azure OpenAI** (or OpenAI) for intelligent memory extraction.

---

## 🎯 Core Principles

### User Personal Memory (Per-User)
- ✅ Personal memory is tied to a **user ID**
- ✅ Personal memory persists across all sessions
- ✅ Only **long-term personal attributes** are stored
- ✅ **Not a full conversation log** - only key facts
- ✅ Automatically extracted from user messages
- ✅ Structured storage in PostgreSQL JSONB format

### What Gets Stored
**✅ Should be stored:**
- Name
- Role or profession
- Preferences (likes, dislikes)
- Skills and expertise
- Location (if relevant)
- Goals and interests
- Language preferences

**❌ Should NOT be stored:**
- Full message transcripts
- Temporary instructions
- One-off questions
- Task-specific context
- Short-term states or plans
- Sensitive data without explicit consent

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PersonalMem App                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Memory Service                         │  │
│  │                                                   │  │
│  │  - User memories (JSONB)                         │  │
│  │  - LLM-based extraction                          │  │
│  │  - Automatic merging                             │  │
│  │  - Structured storage                            │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     │                                    │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │              PostgreSQL                          │  │
│  │        (JSONB column storage)                    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Technologies Used

- **PostgreSQL**: Persistent storage with JSONB for structured memory data
- **FastAPI**: REST API framework
- **Pydantic**: Data validation and modeling
- **Azure OpenAI / OpenAI**: LLM for intelligent memory extraction
- **Python 3.8+**: Core language

---

## 📦 Installation

### Prerequisites

- Python 3.8+
- PostgreSQL (via Docker or local installation)
- Azure OpenAI API key (or regular OpenAI API key)

### 1. Clone or Download

```bash
cd /home/devx/Documents/PersonalMem
```

### 2. Setup Script (Recommended)

```bash
chmod +x setup.sh
./setup.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Guide you through configuration

### 3. Manual Setup

**Create Virtual Environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Install Dependencies:**
```bash
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL

**Option A: Using Docker (Recommended)**

```bash
docker compose up -d postgres
```

This starts PostgreSQL on port 5432 with:
- Database: `personalmem`
- User: `postgres`
- Password: `postgres`

The database schema is automatically initialized via `init_db.sql`.

**Option B: Local PostgreSQL**

Install PostgreSQL locally and create the database:

```sql
CREATE DATABASE personalmem;
```

Then run `init_db.sql` to create the schema.

### 5. Configure Environment

Create a `.env` file in the project root:

```bash
cp env_example.txt .env
```

Edit `.env` with your settings:

```env
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=personalmem
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Option 1: Azure OpenAI (Recommended)
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_MODEL=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-04-01-preview

# Option 2: Regular OpenAI
# OPENAI_API_KEY=sk-your-openai-api-key-here

# Application Settings
LOG_LEVEL=INFO
```

---

## 🚀 Usage

### Option 1: Run the Demo

The demo showcases the core behavior of the system:

```bash
./run_demo.sh
```

Or manually:

```bash
source venv/bin/activate
python app.py
```

**Demo Output:**
```
============================================================
PersonalMem System Demo
============================================================

--- User Message 1 ---
Message: "My name is Alice. I'm a software engineer."
Extracted memories: ['name', 'role']

--- User Message 2 ---
Message: "I love Python and JavaScript."
Extracted memories: ['likes']

--- All Personal Memories for User ---
- Name: Alice
- Role: software engineer
- Likes: ['Python', 'JavaScript']
```

### Option 2: Run the REST API

**Using the startup script:**
```bash
./start_api.sh
```

**Or manually:**
```bash
source venv/bin/activate
uvicorn api:app_api --reload --host 0.0.0.0 --port 8888
```

Visit the interactive API docs at: **http://localhost:8888/docs**

### Option 3: Run with Frontend

```bash
./start_frontend.sh
```

Or manually start the API server, then open **http://localhost:8888** in your browser.

---

## 📚 API Endpoints

### Health Check

**`GET /health`**

Health check endpoint to verify API is running.

**Request:**
- No request body
- No path parameters
- No query parameters

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-20T10:30:45.123456",
  "service": "PersonalMem API"
}
```

**Response Type:**
```typescript
{
  status: string;
  timestamp: string;  // ISO 8601 format
  service: string;
}
```

---

### Message Processing

**`POST /messages`**

Process a user message and automatically extract/update personal memories.

**Request:**
```json
{
  "user_id": "string (required)",
  "message": "string (required)"
}
```

**Request Type:**
```typescript
{
  user_id: string;
  message: string;
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "memory_context": "User Personal Information:\n- name: Alice\n- role: software engineer\n- likes: Python, JavaScript",
  "extracted_memories": [
    {
      "field": "name",
      "value": "Alice",
      "event": "ADD"
    },
    {
      "field": "likes",
      "value": ["Python"],
      "event": "ADD"
    },
    {
      "field": "skills",
      "value": ["react.js"],
      "event": "REMOVE"
    }
  ],
  "message": "Message processed successfully"
}
```

**Response Type:**
```typescript
{
  success: boolean;
  memory_context: string;  // Formatted string of all user memories
  extracted_memories: Array<{
    field: string;      // Memory field name (e.g., "name", "skills", "likes")
    value: string | string[] | number | boolean;  // Field value (can be list for multi-value fields)
    event: "ADD" | "UPDATE" | "REMOVE";  // Type of change
  }>;
  message: string;  // Status message
}
```

**Error Responses:**
- `503 Service Unavailable`: Database connection not available
- `500 Internal Server Error`: Error processing message

**Example:**
```bash
curl -X POST "http://localhost:8888/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "message": "My name is Alice and I love Python."
  }'
```

> **Note:** Memory extraction is **automatic**! The LLM analyzes every message to detect long-term personal information. Items can be added, updated, or removed based on the message content.

---

### Memory Management

**`GET /users/{user_id}/memories`**

Get all memories for a specific user.

**Path Parameters:**
- `user_id` (string, required): User identifier

**Response (200 OK):**
```json
[
  {
    "id": "user_123_name",
    "memory": "name: Alice",
    "user_id": "user_123",
    "created_at": "2025-01-20T10:30:45.123456",
    "updated_at": "2025-01-20T10:30:45.123456"
  },
  {
    "id": "user_123_skills",
    "memory": "skills: Python, JavaScript, React",
    "user_id": "user_123",
    "created_at": "2025-01-20T10:35:12.789012",
    "updated_at": "2025-01-20T11:20:30.456789"
  }
]
```

**Response Type:**
```typescript
Array<{
  id: string;              // Format: "{user_id}_{field_name}"
  memory: string;          // Formatted as "{field}: {value}"
  user_id: string | null;  // User identifier
  created_at: string | null;  // ISO 8601 timestamp
  updated_at: string | null;  // ISO 8601 timestamp
}>
```

**Empty Response (200 OK):**
```json
[]
```

**Error Responses:**
- `503 Service Unavailable`: Database connection not available
- `500 Internal Server Error`: Error retrieving memories

**Example:**
```bash
curl -X GET "http://localhost:8888/users/user_123/memories"
```

---

**`GET /users/{user_id}/memories/search`**

Search user memories (keyword-based search within memory content).

**Path Parameters:**
- `user_id` (string, required): User identifier

**Query Parameters:**
- `query` (string, required): Search query
- `limit` (integer, optional): Maximum number of results (default: 5)

**Response (200 OK):**
```json
[
  {
    "id": "user_123_skills",
    "memory": "skills: Python, JavaScript, React",
    "user_id": "user_123",
    "created_at": "2025-01-20T10:35:12.789012",
    "updated_at": "2025-01-20T11:20:30.456789"
  }
]
```

**Response Type:**
```typescript
Array<{
  id: string;
  memory: string;
  user_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}>
```

**Example:**
```bash
curl -X GET "http://localhost:8888/users/user_123/memories/search?query=Python&limit=5"
```

---

**`DELETE /users/{user_id}/memories`**

Delete all memories for a user.

**Path Parameters:**
- `user_id` (string, required): User identifier

**Response (200 OK):**
```json
{
  "message": "All memories deleted for user user_123"
}
```

**Response Type:**
```typescript
{
  message: string;
}
```

**Error Responses:**
- `500 Internal Server Error`: Failed to delete memories

**Example:**
```bash
curl -X DELETE "http://localhost:8888/users/user_123/memories"
```

---

**`DELETE /memories/{memory_id}`**

Delete a specific memory by ID.

**Path Parameters:**
- `memory_id` (string, required): Memory ID (format: "{user_id}_{field_name}")

**Response (200 OK):**
```json
{
  "message": "Memory user_123_skills deleted"
}
```

**Response Type:**
```typescript
{
  message: string;
}
```

**Error Responses:**
- `404 Not Found`: Memory not found
- `500 Internal Server Error`: Error deleting memory

**Example:**
```bash
curl -X DELETE "http://localhost:8888/memories/user_123_skills"
```

---

**`GET /users/{user_id}/context`**

Get complete context for a user (all memories in structured format).

**Path Parameters:**
- `user_id` (string, required): User identifier

**Response (200 OK):**
```json
{
  "user_memories": [
    {
      "id": "user_123_name",
      "memory": "name: Alice",
      "user_id": "user_123",
      "created_at": "2025-01-20T10:30:45.123456",
      "updated_at": "2025-01-20T10:30:45.123456"
    }
  ],
  "user_id": "user_123"
}
```

**Response Type:**
```typescript
{
  user_memories: Array<{
    id: string;
    memory: string;
    user_id: string | null;
    created_at: string | null;
    updated_at: string | null;
  }>;
  user_id: string;
}
```

**Error Responses:**
- `500 Internal Server Error`: Error retrieving context

**Example:**
```bash
curl -X GET "http://localhost:8888/users/user_123/context"
```

---

### API Endpoints Summary

| Method | Endpoint | Request Body | Response Type | Description |
|--------|----------|--------------|---------------|-------------|
| `GET` | `/health` | None | `{status, timestamp, service}` | Health check |
| `POST` | `/messages` | `{user_id, message}` | `{success, memory_context, extracted_memories, message}` | Process message and extract memories |
| `GET` | `/users/{user_id}/memories` | None | `Array<MemoryInfo>` | Get all user memories |
| `GET` | `/users/{user_id}/memories/search` | Query: `query`, `limit` | `Array<MemoryInfo>` | Search user memories |
| `DELETE` | `/users/{user_id}/memories` | None | `{message}` | Delete all user memories |
| `DELETE` | `/memories/{memory_id}` | None | `{message}` | Delete specific memory |
| `GET` | `/users/{user_id}/context` | None | `{user_memories, user_id}` | Get complete user context |

**MemoryInfo Type:**
```typescript
{
  id: string;              // Format: "{user_id}_{field_name}"
  memory: string;          // Formatted as "{field}: {value}"
  user_id: string | null;
  created_at: string | null;  // ISO 8601 timestamp
  updated_at: string | null;  // ISO 8601 timestamp
}
```

**Extracted Memory Type:**
```typescript
{
  field: string;      // Field name (e.g., "name", "skills", "likes")
  value: string | string[] | number | boolean;  // Field value
  event: "ADD" | "UPDATE" | "REMOVE";  // Change type
}
```

---

## 🧠 How Memory Extraction Works

### ⚡ Automatic Extraction

**Every message is automatically analyzed by the LLM** to determine if it contains long-term personal information. The system uses a carefully crafted prompt to:

- ✅ Extract only permanent attributes and preferences
- ✅ Filter out temporary states and task-specific context
- ✅ Merge new information with existing memories
- ✅ Handle list-based attributes (e.g., likes, skills)

### Extraction Process

1. **Message Analysis**: User message is sent to LLM with extraction prompt
2. **Fact Extraction**: LLM returns structured JSON with personal facts
3. **Memory Merging**: New facts are merged with existing memories
4. **Storage**: Updated memories are stored in PostgreSQL JSONB format

### Example Behavior

```python
# User says:
"My name is Alice. I'm a software engineer."

# System extracts:
{
  "name": "Alice",
  "role": "software engineer"
}

# User says later:
"I love Python and JavaScript."

# System extracts and merges:
{
  "name": "Alice",
  "role": "software engineer",
  "likes": ["Python", "JavaScript"]
}

# User says:
"I need help debugging this function."

# System does NOT store this (task-specific, not personal)
```

---

## 🗄️ Database Schema

### user_memories Table

```sql
CREATE TABLE user_memories (
    user_id TEXT PRIMARY KEY,
    memories JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_memories_gin ON user_memories USING GIN (memories);
```

### Example Memory Structure

```json
{
  "name": "Alice",
  "role": "software engineer",
  "likes": ["Python", "JavaScript", "pizza"],
  "dislikes": ["tomato"],
  "skills": ["backend development", "API design"],
  "location": "New York"
}
```

---

## 🔧 Project Structure

```
PersonalMem/
├── api.py                  # FastAPI REST API
├── app.py                  # Main application with demo
├── config.py               # Configuration management
├── memory_service.py       # User memory management (PostgreSQL + LLM)
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # PostgreSQL service
├── init_db.sql            # Database schema initialization
├── env_example.txt        # Example environment variables
├── setup.sh               # Setup script
├── start_api.sh           # API server startup script
├── start_frontend.sh      # Frontend + API startup script
├── run_demo.sh            # Demo runner script
├── restart_postgres.sh    # PostgreSQL restart script
└── frontend/              # Web frontend
    ├── index.html
    ├── app.js
    └── styles.css
```

---

## 🎮 Example Scenarios

### Scenario 1: Name Persistence

```python
# First message
user: "My name is Alice."
system: Extracts {"name": "Alice"}

# Later message
user: "What did I tell you my name was?"
system: Retrieves from memory: "Alice"
```

### Scenario 2: Preference Tracking

```python
# First message
user: "I love Python and pizza."
system: Extracts {"likes": ["Python", "pizza"]}

# Later message
user: "I also like JavaScript."
system: Merges: {"likes": ["Python", "pizza", "JavaScript"]}
```

### Scenario 3: Task Context (Not Stored)

```python
# User message
user: "I need help debugging this function."
system: Does NOT store (task-specific, not personal)

# Later message
user: "What was I asking about earlier?"
system: Cannot retrieve (correctly not stored)
```

---

## 🔒 Privacy & Data Management

### User Rights

Users can:
- ✅ **View** all their memories: `GET /users/{user_id}/memories`
- ✅ **Update** specific memories: `PUT /users/{user_id}/memories/{key}`
- ✅ **Delete** specific memories: `DELETE /users/{user_id}/memories/{key}`
- ✅ **Opt-out** completely: `DELETE /users/{user_id}/memories`

### Data Storage

- **User memories** are stored in PostgreSQL (JSONB format)
- Memories are **never** full message transcripts
- Each memory is independently manageable
- Data is structured for easy querying and updates

---

## 🛠️ Development

### Database Management

**Restart PostgreSQL (with fresh schema):**
```bash
./restart_postgres.sh
```

**View PostgreSQL logs:**
```bash
docker compose logs postgres
```

**Connect to PostgreSQL:**
```bash
docker compose exec postgres psql -U postgres -d personalmem
```

### Testing

The API can be tested using:
- Interactive docs: http://localhost:8888/docs
- Frontend interface: http://localhost:8888/
- curl commands (see API Endpoints section)

---

## 🚀 Production Deployment

### Environment Variables for Production

```env
# Production PostgreSQL
POSTGRES_HOST=your-postgres-host
POSTGRES_PORT=5432
POSTGRES_DB=personalmem
POSTGRES_USER=your-user
POSTGRES_PASSWORD=your-secure-password

# Secure your API keys
AZURE_OPENAI_API_KEY=your-production-key
# or
OPENAI_API_KEY=sk-your-production-key

# Set appropriate log level
LOG_LEVEL=WARNING
```

### Docker Deployment

**Build API container:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api:app_api", "--host", "0.0.0.0", "--port", "8888"]
```

**Build and run:**
```bash
docker build -t personalmem .
docker run -p 8888:8888 --env-file .env --link personalmem_postgres:postgres personalmem
```

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - feel free to use this in your projects!

---

## 🙏 Acknowledgments

- **PostgreSQL** - Robust relational database with JSONB support
- **Azure OpenAI / OpenAI** - Powerful LLM for memory extraction
- **FastAPI** - Modern web framework
- **ChatGPT** - Inspiration for personal memory feature

---

## 📞 Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

## 🎯 Features

- ✅ Automatic memory extraction from user messages
- ✅ Long-term personal information persistence
- ✅ Structured storage in PostgreSQL JSONB
- ✅ LLM-powered intelligent extraction
- ✅ Memory inspection and management
- ✅ Memory deletion (specific or all)
- ✅ RESTful API interface
- ✅ Web frontend for testing
- ✅ Docker-based PostgreSQL setup

---

**Built with ❤️ using PostgreSQL and Azure OpenAI**
