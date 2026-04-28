# PersonalMem

Personal memory management API that extracts and stores user information from messages using an LLM. Built for chatbot backends that need to remember user preferences, context, and personal details across conversations.

**API v3 — frontend-friendly.** Every mutation returns the full updated user state, so a UI can `setState(response)` without a refetch.

## Features

- **Automatic Memory Extraction** — LLM analyzes a sentence and extracts personal information
- **Direct Edits Without the LLM** — `set` / `append` / `remove` / `delete` / `bulk_set` via a single `PATCH` endpoint
- **Single-Call Loads** — `GET /users/{id}` returns memories, formatted prompt text, counts, and timestamps in one shot
- **Smart Merging** — list dedupe, conflict resolution (`likes` ↔ `dislikes`), partial removals
- **Flexible Schema** — schema-less MongoDB; new fields appear automatically
- **Chatbot Ready** — every response includes a `context_text` field ready to drop into a system prompt
- **GDPR Compliant** — hard-delete a user with `DELETE /users/{id}`

## Tech Stack

- **FastAPI** — REST API framework
- **MongoDB** — flexible document storage
- **Azure OpenAI / OpenAI** — LLM for memory extraction
- **Docker** — containerized deployment

## Quick Start

### Option 1: Docker (recommended)

```bash
cp env.template .env
# edit .env and add your AZURE_OPENAI_API_KEY (or OPENAI_API_KEY)

docker compose up --build -d
```

Access:
- API: <http://localhost:8888/docs>
- MongoDB: localhost:27017 (admin / admin123)

> Note: `docker-compose.yml` runs the API and MongoDB as **two separate containers** (`personalmem-api` and `personalmem-mongodb`) sharing a Docker network.

### Option 2: Local development

```bash
docker compose up -d mongodb           # just the database
cp env.template .env                   # then edit .env
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn api:app --reload --host 0.0.0.0 --port 8888
```

## API Overview

Five endpoints. The full `UserState` shape (returned by all four user endpoints) is:

```json
{
  "user_id": "alice123",
  "memories": { "name": "Alice", "skills": ["Rust"] },
  "context_text": "User Information:\n- name: Alice\n- skills: Rust",
  "has_memories": true,
  "field_count": 2,
  "created_at": 1730...,
  "updated_at": 1730...
}
```

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/users/{user_id}` | Load full user state |
| `POST` | `/users/{user_id}/messages` | LLM-extract memories from a sentence |
| `PATCH` | `/users/{user_id}` | Direct mutation via action verb (no LLM) |
| `DELETE` | `/users/{user_id}` | Wipe the user |

---

### `GET /users/{user_id}`

Load everything the UI needs in one call.

**Response:** `UserState` (see shape above). For a non-existent user, returns the same shape with empty `memories`, `has_memories: false`, and `null` timestamps.

---

### `POST /users/{user_id}/messages`

LLM extracts personal info from a sentence and merges it into the user's memory.

**Request:**
```json
{ "message": "My name is John and I love Python" }
```

**Response:** `UserState` plus:
```json
{
  "extracted_memories": [
    { "field": "name",   "value": "John",       "event": "ADD" },
    { "field": "likes",  "value": ["Python"],   "event": "ADD" }
  ],
  "response_time_ms": 850
}
```

`event` is one of: `ADD`, `UPDATE`, `REPLACE`, `REMOVE`.

---

### `PATCH /users/{user_id}`

Direct mutation via an action verb. Skips the LLM, runs in milliseconds, free.

| Action | Body | Effect |
|---|---|---|
| `set` | `{action:"set", field:"name", value:"Alice"}` | Replace any field. Lists overwrite, scalars replace. |
| `append` | `{action:"append", field:"skills", value:"Rust"}` | Add to a list (dedupes). `value` may be a single item or list. Auto-creates the list if missing. |
| `remove` | `{action:"remove", field:"skills", value:"Python"}` | Remove item(s) from a list. Deletes the field if the list becomes empty. |
| `delete` | `{action:"delete", field:"age"}` | Drop a whole field. |
| `bulk_set` | `{action:"bulk_set", values:{"name":"A","age":29}}` | Multi-field set in one call. |

**Response:** `UserState` plus a `changes` array describing what was modified.

Validation errors return `400` with a descriptive message.

---

### `DELETE /users/{user_id}`

Hard-deletes the user's document. Returns the empty post-delete `UserState` (200), even if the user didn't exist.

---

## Chatbot Integration Example

```python
import requests, openai

API = "http://localhost:8888"

def chat_with_memory(user_id: str, user_message: str):
    # 1. Extract & store memories AND get the updated context in one call
    r = requests.post(f"{API}/users/{user_id}/messages",
                      json={"message": user_message}).json()
    system_prompt = f"You are a helpful assistant.\n\n{r['context_text']}"

    # 2. Call your chatbot with the prepared prompt
    return openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ]
    ).choices[0].message.content
```

If you only need to *read* the context (e.g. on every turn without writing):

```python
ctx = requests.get(f"{API}/users/{user_id}").json()["context_text"]
```

## Frontend Integration Example

```js
const Mem = {
    load:    (uid)               => fetch(`/users/${uid}`).then(r => r.json()),
    chat:    (uid, message)      => POST(`/users/${uid}/messages`, { message }),
    set:     (uid, field, value) => PATCH(`/users/${uid}`, { action: 'set',    field, value }),
    append:  (uid, field, value) => PATCH(`/users/${uid}`, { action: 'append', field, value }),
    remove:  (uid, field, value) => PATCH(`/users/${uid}`, { action: 'remove', field, value }),
    delete:  (uid, field)        => PATCH(`/users/${uid}`, { action: 'delete', field }),
    wipe:    (uid)               => fetch(`/users/${uid}`, { method: 'DELETE' }).then(r => r.json()),
};

// Every mutation returns the full new UserState — no refetch.
const state = await Mem.append('alice', 'skills', 'Rust');
renderUI(state);
```

## What Gets Extracted

The LLM extracts and categorizes personal information across these areas:

| Category | Example Fields |
|---|---|
| Identity | name, nickname, age, birthday, gender, nationality |
| Location | location, hometown, timezone, address |
| Work | role, company, jobs[], industry, skills, education |
| Preferences | likes, dislikes, hobbies, interests, favorite_* |
| Lifestyle | diet, exercise, sleep_schedule, work_style |
| Relationships | family, pets, partner_name, children |
| Languages | languages, native_language, learning_languages |
| Health | allergies, health_conditions, blood_type |
| Personality | personality_traits, values, life_goals, fears |
| Other | habits, achievements, travel_history, bucket_list |

The schema is flexible — fields are created on demand.

## Configuration

### Environment variables (`.env`)

```env
# MongoDB
MONGODB_URI=mongodb://admin:admin123@localhost:27017/
MONGODB_DATABASE=personalmem

# Azure OpenAI (recommended)
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_MODEL=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-04-01-preview

# OR plain OpenAI
# OPENAI_API_KEY=sk-...

LOG_LEVEL=INFO
```

### MongoDB credentials

Defaults: `admin` / `admin123` on port `27017`, database `personalmem`. Override in `docker-compose.yml` and `MONGODB_URI`.

## Data Schema

One document per user in collection `user_memories`:

```json
{
  "_id": ObjectId("..."),
  "user_id": "alice123",
  "memories": {
    "name": "Alice",
    "age": 29,
    "skills": ["Rust", "Go"],
    "likes": ["coffee"]
  },
  "created_at": 1730000000.0,
  "updated_at": 1730000050.5
}
```

Indexed on `user_id` (unique). Lists are appended/deduped; scalars are replaced; `likes` and `dislikes` automatically resolve conflicts.

## Testing

```bash
# Make sure the API is running, then:
python test_memory_updates.py
```

Covers LLM extraction, all five PATCH actions, validation errors, and delete-empty semantics.

## Troubleshooting

### MongoDB connection issues

```bash
docker ps | grep mongodb            # is it running?
docker compose up -d mongodb         # start it
docker compose down -v && docker compose up -d   # nuke + restart
```

| Issue | Fix |
|---|---|
| "Cannot connect to MongoDB" | `docker compose up -d` |
| "Authentication failed" | check `.env` credentials |
| "Database connection not available" | wait 5–10s for Mongo to start, retry |
| Port 27017 in use | stop other Mongo or change port in `docker-compose.yml` |

### `sudo docker compose up` fails with TLS handshake timeout

You're likely already in the `docker` group — drop the `sudo`:

```bash
docker compose up --build
```

`sudo` runs docker as root with a stripped environment, which can break the daemon's auth/registry path on some setups.

### API not starting

```bash
pip install -r requirements.txt
lsof -i :8888                                       # is the port free?
LOG_LEVEL=DEBUG uvicorn api:app --reload --port 8888
```

## Project Structure

```
PersonalMem/
├── api.py                 # FastAPI app — 5 endpoints
├── memory_service.py      # LLM extraction, merge logic, MongoDB I/O
├── config.py              # Env loading + validation
├── docker-compose.yml     # API + MongoDB containers
├── Dockerfile             # API image
├── requirements.txt       # Python dependencies
├── env.template           # Copy to .env and fill in
└── test_memory_updates.py # Integration tests
```

## License

MIT — use freely.
