# PersonalMem Architecture

## System Overview

PersonalMem is a dual-storage system that separates **transient chat history** from **persistent user memory**.

```
┌─────────────────────────────────────────────────────────────┐
│                         User Input                          │
│                   "My name is Honda"                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    PersonalMemApp                           │
│                  (Main Application)                         │
└───────────┬──────────────────────────┬──────────────────────┘
            │                          │
            ▼                          ▼
┌───────────────────────┐  ┌──────────────────────────┐
│   ChatService         │  │   MemoryService          │
│                       │  │                          │
│ - Per-chat storage    │  │ - Per-user storage       │
│ - Message history     │  │ - Semantic search        │
│ - Isolated chats      │  │ - Auto-extraction        │
│ - CRUD operations     │  │ - Intelligent filtering  │
└───────────┬───────────┘  └──────────┬───────────────┘
            │                         │
            ▼                         ▼
┌───────────────────────┐  ┌──────────────────────────┐
│      MongoDB          │  │       mem0               │
│                       │  │                          │
│ Collections:          │  │ Components:              │
│ - chats               │  │ - Vector Store (Qdrant)  │
│   - chat_id (PK)      │  │ - LLM (OpenAI)          │
│   - user_id (IDX)     │  │ - Embeddings (OpenAI)    │
│   - messages[]        │  │ - Memory Graph           │
│   - metadata          │  │                          │
└───────────────────────┘  └──────────────────────────┘
```

## Data Flow

### 1. User Sends Message

```
User → API → PersonalMemApp.process_user_message()
                    │
                    ├─→ ChatService.add_message()
                    │        └─→ MongoDB (chats collection)
                    │
                    └─→ MemoryService.add_memory_from_message()
                             └─→ mem0 → Vector DB + LLM
```

### 2. Generate Response

```
User Query → PersonalMemApp.get_user_context()
                    │
                    ├─→ ChatService.get_chat_history()
                    │        └─→ MongoDB (current chat only)
                    │
                    └─→ MemoryService.get_memory_context()
                             └─→ mem0 → Semantic Search
                    
Combined Context → LLM → Response
```

## Component Details

### 1. ChatService (chat_service.py)

**Purpose:** Manage isolated chat sessions

**Storage:** MongoDB

**Key Operations:**
- `create_chat()` - Create new chat session
- `add_message()` - Append message to chat
- `get_chat_history()` - Retrieve messages (single chat only)
- `delete_chat()` - Remove chat and all messages

**Data Model:**
```json
{
  "chat_id": "uuid",
  "user_id": "string",
  "title": "string",
  "messages": [
    {
      "role": "user|assistant|system",
      "content": "string",
      "timestamp": "datetime"
    }
  ],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 2. MemoryService (memory_service.py)

**Purpose:** Manage persistent user memories

**Storage:** mem0 (Qdrant vector DB)

**Key Operations:**
- `add_memory_from_message()` - Extract and store memories
- `get_all_memories()` - Retrieve all user memories
- `search_memories()` - Semantic search
- `delete_memory()` - Remove specific memory
- `delete_all_memories()` - Clear user memories

**Memory Extraction Process:**
```
Input: "My name is Honda and I love Python"
    ↓
mem0 LLM Analysis
    ↓
Extracted Memories:
- "User's name is Honda"
- "User loves Python"
    ↓
Vector Embeddings Created
    ↓
Stored in Qdrant
```

### 3. PersonalMemApp (app.py)

**Purpose:** Coordinate chat and memory services

**Key Operations:**
- `process_user_message()` - Handle incoming messages
- `get_user_context()` - Combine chat + memory for responses
- `create_new_chat()` - Start new chat session

### 4. FastAPI (api.py)

**Purpose:** REST API interface

**Key Endpoints:**
- POST `/chats` - Create chat
- POST `/chats/messages` - Send message
- GET `/users/{user_id}/memories` - View memories
- DELETE `/memories/{memory_id}` - Delete memory

## Memory vs Chat: Critical Differences

| Aspect | Chat History | User Memory |
|--------|-------------|-------------|
| **Scope** | Single chat | All chats |
| **Storage** | MongoDB | mem0/Qdrant |
| **Content** | Full messages | Extracted facts |
| **Access** | Only within chat | Across all chats |
| **Lifespan** | Chat duration | User lifetime |
| **Size** | Can be large | Small, curated |

## Memory Extraction Intelligence

### What mem0 Stores

✅ **Stores:**
- Identity: "User's name is Honda"
- Profession: "User is a software engineer"
- Preferences: "User prefers Python over JavaScript"
- Skills: "User knows machine learning"
- Goals: "User wants to learn Rust"

❌ **Filters Out:**
- Questions: "What is recursion?"
- Commands: "Debug this function"
- Temporary context: "I'm working on feature X today"
- Task-specific: "This function has a bug"

### How mem0 Works

1. **Analysis:** LLM analyzes message for personal information
2. **Extraction:** Identifies meaningful, long-term facts
3. **Deduplication:** Checks against existing memories
4. **Update:** Merges or updates similar memories
5. **Storage:** Stores as vector embeddings + metadata

## Scaling Considerations

### For Production

**MongoDB:**
- Use MongoDB Atlas for cloud hosting
- Enable replica sets for high availability
- Index on `user_id` and `chat_id`
- Implement TTL for old chats

**mem0:**
- Use hosted Qdrant or Pinecone for vector storage
- Implement caching for frequently accessed memories
- Rate limit memory extraction

**API:**
- Deploy with gunicorn + multiple workers
- Add Redis for session management
- Implement rate limiting (e.g., slowapi)
- Add authentication (OAuth2/JWT)

## Security Considerations

1. **Data Isolation:** Each user's memories are strictly isolated
2. **Access Control:** Implement user authentication
3. **Encryption:** Encrypt sensitive data at rest
4. **Audit Logs:** Track memory access and modifications
5. **GDPR Compliance:** Support right to deletion

## Extension Points

### Adding New Features

1. **Memory Categories:**
   ```python
   # Add categories to memories
   class MemoryCategory(Enum):
       PERSONAL = "personal"
       PROFESSIONAL = "professional"
       PREFERENCES = "preferences"
   ```

2. **Memory Confidence Scoring:**
   ```python
   # Already supported in models.py
   memory.confidence = 0.95  # High confidence
   ```

3. **Multi-User Chats:**
   ```python
   # Extend Chat model
   class Chat(BaseModel):
       chat_id: str
       user_ids: List[str]  # Multiple users
       ...
   ```

4. **Memory Analytics:**
   ```python
   def get_memory_statistics(user_id: str) -> Dict:
       memories = memory_service.get_all_memories(user_id)
       return {
           "total_memories": len(memories),
           "oldest_memory": min(m['created_at']),
           "categories": count_by_category(memories)
       }
   ```

## Testing Strategy

### Unit Tests
- Test models (Chat, Message)
- Test utility functions
- Mock external dependencies

### Integration Tests
- Test with real MongoDB
- Test with real mem0
- Test API endpoints

### End-to-End Tests
- Simulate multi-chat scenarios
- Verify memory persistence
- Verify chat isolation

## Performance Metrics

**Target Metrics:**
- Message processing: < 500ms
- Memory retrieval: < 200ms
- Chat history load: < 100ms
- API response time: < 1s

## Monitoring

**Key Metrics to Track:**
- Memory extraction success rate
- Memory deduplication rate
- API response times
- MongoDB query performance
- Vector search latency
- Error rates

---

**This architecture ensures strict separation of concerns while providing intelligent, context-aware user experiences.**

