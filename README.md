# PersonalMem: Personalized User Memory System

A chat-based application system that remembers **key personal information about users across all chats**, while keeping **conversation history isolated per chat session**.

This system is inspired by ChatGPT's **personal memory** feature, built with **mem0** (AI memory layer) and **MongoDB**.

---

## 🎯 Core Principles

### 1. Chat History (Per-Chat)
- ✅ Chat messages belong to a single chat session
- ✅ Chat history is **not shared** across chats
- ✅ Starting a new chat does **not** load previous chat messages
- ✅ Chat history is only used within its own chat

### 2. User Personal Memory (Per-User)
- ✅ Personal memory is tied to a **user ID**, not a chat ID
- ✅ Personal memory is shared across **all chats**
- ✅ Personal memory persists even when a new chat is created
- ✅ Only **high-signal, long-term user attributes** are stored
- ✅ **Not a full conversation log**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PersonalMem App                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────────────┐      ┌──────────────────────┐ │
│  │   Chat Service     │      │   Memory Service     │ │
│  │                    │      │                      │ │
│  │  - Isolated chats  │      │  - User memories     │ │
│  │  - Message history │      │  - Semantic search   │ │
│  │  - Per-chat data   │      │  - Auto-extraction   │ │
│  │                    │      │  - Deduplication     │ │
│  └──────┬─────────────┘      └──────┬───────────────┘ │
│         │                           │                  │
│         ▼                           ▼                  │
│  ┌─────────────┐            ┌──────────────┐          │
│  │  MongoDB    │            │    mem0      │          │
│  │  (Chats)    │            │  (Memories)  │          │
│  └─────────────┘            └──────────────┘          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Technologies Used

- **[mem0](https://github.com/mem0ai/mem0)**: AI-powered memory layer with intelligent extraction and retrieval
- **MongoDB**: Persistent storage for chat history
- **FastAPI**: REST API framework
- **Pydantic**: Data validation and modeling
- **Python 3.8+**: Core language

---

## 📦 Installation

### Prerequisites

- Python 3.8+
- MongoDB (local or cloud)
- OpenAI API key (or other LLM provider supported by mem0)

### 1. Clone or Download

```bash
cd /home/devx/Documents/PersonalMem
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up MongoDB

**Option A: Using Docker (Recommended)**

```bash
docker-compose up -d
```

This starts:
- MongoDB on port 27017
- MongoDB Express (UI) on port 8081

**Option B: Local MongoDB**

Install MongoDB locally and ensure it's running on `mongodb://localhost:27017/`

### 5. Configure Environment

Create a `.env` file in the project root:

```bash
cp env_example.txt .env
```

Edit `.env` with your settings:

```env
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=personalmem

# OpenAI API Key (required for mem0)
OPENAI_API_KEY=sk-your-actual-openai-api-key-here

# Application Settings
LOG_LEVEL=INFO
```

---

## 🚀 Usage

### Option 1: Run the Demo

The demo showcases the core behavior of the system:

```bash
python app.py
```

**Demo Output:**
```
============================================================
PersonalMem System Demo
============================================================

--- CHAT A: User introduces themselves ---
Created Chat A: 12345...
Extracted memories: 2

--- CHAT B: New chat (should remember name) ---
Created Chat B: 67890...

Memory context available for response:
User Personal Information (from previous conversations):
- User's name is Honda
- User is a software engineer who loves Python
- User prefers working on backend systems

--- All Personal Memories for User ---
1. User's name is Honda
2. User is a software engineer who loves Python
3. User prefers working on backend systems

--- Chat Isolation Check ---
Chat A messages: 4
Chat B messages: 2
Chat C messages: 2
```

### Option 2: Run the REST API

Start the FastAPI server:

```bash
python api.py
```

Or using uvicorn directly:

```bash
uvicorn api:app_api --reload --host 0.0.0.0 --port 8000
```

Visit the interactive API docs at: **http://localhost:8000/docs**

---

## 📚 API Endpoints

### Chat Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chats` | Create a new chat session |
| `GET` | `/users/{user_id}/chats` | Get all chats for a user |
| `GET` | `/chats/{chat_id}/messages` | Get messages in a chat |
| `POST` | `/chats/messages` | Send a user message |
| `POST` | `/chats/responses` | Add assistant response |
| `DELETE` | `/chats/{chat_id}` | Delete a chat |

### Memory Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users/{user_id}/memories` | Get all user memories |
| `DELETE` | `/memories/{memory_id}` | Delete a specific memory |
| `DELETE` | `/users/{user_id}/memories` | Delete all user memories |
| `GET` | `/users/{user_id}/context/{chat_id}` | Get context for response generation |

### Example API Usage

**1. Create a Chat**

```bash
curl -X POST "http://localhost:8000/chats" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "title": "My First Chat"
  }'
```

**2. Send a Message**

```bash
curl -X POST "http://localhost:8000/chats/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "chat_id": "chat_abc",
    "message": "My name is Honda and I love Python.",
    "extract_memory": true
  }'
```

**3. Get User Memories**

```bash
curl -X GET "http://localhost:8000/users/user_123/memories"
```

**4. Get Context for Response**

```bash
curl -X GET "http://localhost:8000/users/user_123/context/chat_abc"
```

---

## 🧠 How Memory Extraction Works

### What Gets Stored

**✅ Should be stored:**
- Name
- Role or profession
- Preferences
- Goals
- Language preference
- Repeated constraints or interests

**❌ Should NOT be stored:**
- Full chat transcripts
- Temporary instructions
- One-off questions
- Task-specific context
- Sensitive data without explicit consent

### Automatic Filtering by mem0

The system uses **mem0** which intelligently:
1. **Extracts** only meaningful, long-term information
2. **Deduplicates** similar memories
3. **Updates** existing memories when new information arrives
4. **Filters out** temporary or task-specific content

### Example Behavior

```python
# User says in Chat A:
"My name is Honda. I'm a software engineer."

# mem0 extracts:
# - "User's name is Honda"
# - "User is a software engineer"

# User says in Chat B (different chat):
"What is my name?"

# System retrieves from memory:
# "User's name is Honda"
# Response: "Your name is Honda."

# User says in Chat C:
"Help me debug this function."

# mem0 does NOT store this (task-specific, not personal)
```

---

## 🔧 Project Structure

```
PersonalMem/
├── app.py                  # Main application with demo
├── api.py                  # FastAPI REST API
├── config.py               # Configuration management
├── models.py               # Data models (Chat, Message, Memory)
├── memory_service.py       # User memory management (mem0)
├── chat_service.py         # Chat history management (MongoDB)
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # MongoDB + Mongo Express
├── env_example.txt         # Example environment variables
├── .gitignore             # Git ignore file
└── README.md              # This file
```

---

## 🎮 Example Scenarios

### Scenario 1: Name Persistence

```python
# Chat A
user: "My name is Honda."
assistant: "Nice to meet you, Honda!"

# Chat B (new chat)
user: "What is my name?"
assistant: "Your name is Honda."  # Retrieved from memory
```

### Scenario 2: Task Context (Not Stored)

```python
# Chat A
user: "I need help debugging this function: def add(a,b): return a-b"
# mem0 correctly identifies this as task-specific and doesn't store it

# Chat B
user: "What was I asking about earlier?"
assistant: "I don't have information about previous chats."  # Correct!
```

### Scenario 3: Preference Tracking

```python
# Chat A
user: "I prefer Python over JavaScript."

# Chat B (weeks later)
user: "What language should I use for my backend?"
assistant: "Based on your preference for Python, I'd recommend..."
```

---

## 🔒 Privacy & Data Management

### User Rights

Users can:
- ✅ **View** all their memories: `GET /users/{user_id}/memories`
- ✅ **Delete** specific memories: `DELETE /memories/{memory_id}`
- ✅ **Opt-out** completely: `DELETE /users/{user_id}/memories`

### Data Separation

- **Chat history** is stored in MongoDB
- **User memories** are stored in mem0 (Qdrant vector DB)
- Memories are **never** full chat transcripts
- Each memory is independently manageable

---

## 🛠️ Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Linting

```bash
# Install linting tools
pip install flake8 black

# Format code
black .

# Check code quality
flake8 .
```

---

## 🚀 Production Deployment

### Environment Variables for Production

```env
# Use production MongoDB (e.g., MongoDB Atlas)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/

# Secure your API keys
OPENAI_API_KEY=sk-your-production-key

# Set appropriate log level
LOG_LEVEL=WARNING
```

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api:app_api", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t personalmem .
docker run -p 8000:8000 --env-file .env personalmem
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

- **[mem0](https://github.com/mem0ai/mem0)** - Intelligent memory layer for AI applications
- **MongoDB** - Document database for chat storage
- **FastAPI** - Modern web framework

---

## 📞 Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

## 🎯 Definition of Done ✅

- ✅ User personal information persists across chats
- ✅ Chat conversations remain isolated
- ✅ Only selective personal data is stored
- ✅ Behavior matches the specified examples
- ✅ Memory inspection supported
- ✅ Memory deletion supported
- ✅ Memory opt-out per user supported

---

**Built with ❤️ using mem0 and MongoDB**

