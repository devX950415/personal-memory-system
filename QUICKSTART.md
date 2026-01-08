# PersonalMem Quick Start Guide

Get up and running with PersonalMem in 5 minutes!

## Prerequisites

- Python 3.8+
- Docker (for MongoDB)
- OpenAI API Key

## Step 1: Setup (2 minutes)

```bash
# Run the setup script
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 2: Configure (1 minute)

```bash
# Copy the example environment file
cp env_example.txt .env

# Edit with your API key
nano .env
```

Add your OpenAI API key:
```env
OPENAI_API_KEY=sk-your-actual-key-here
```

## Step 3: Start MongoDB (30 seconds)

```bash
docker-compose up -d
```

This starts MongoDB on port 27017 and MongoDB Express (UI) on port 8081.

## Step 4: Run (1 minute)

### Option A: Run the Demo

```bash
./run_demo.sh

# Or manually:
source venv/bin/activate
python app.py
```

The demo will show you:
- Creating chats
- Storing memories
- Retrieving memories across chats
- Chat isolation

### Option B: Start the API Server

```bash
./start_api.sh

# Or manually:
source venv/bin/activate
python api.py
```

Visit http://localhost:8000/docs for interactive API documentation.

## First API Call

Try creating a chat:

```bash
curl -X POST "http://localhost:8000/chats" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "title": "My First Chat"
  }'
```

Send a message with personal info:

```bash
curl -X POST "http://localhost:8000/chats/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "chat_id": "YOUR_CHAT_ID",
    "message": "My name is Alice and I love machine learning.",
    "extract_memory": true
  }'
```

Check stored memories:

```bash
curl "http://localhost:8000/users/alice/memories"
```

## What's Next?

1. Read the full [README.md](README.md) for detailed documentation
2. Explore the API at http://localhost:8000/docs
3. Check the MongoDB UI at http://localhost:8081
4. Look at the code examples in `app.py`

## Troubleshooting

**MongoDB not running?**
```bash
docker-compose up -d
```

**Port 27017 already in use?**
```bash
# Change the port in docker-compose.yml
ports:
  - "27018:27017"  # Use 27018 instead

# Update .env
MONGODB_URI=mongodb://localhost:27018/
```

**Missing OpenAI API key?**
```bash
# Make sure .env file exists and has your key
cat .env | grep OPENAI_API_KEY
```

## Clean Up

Stop MongoDB:
```bash
docker-compose down
```

Remove virtual environment:
```bash
deactivate
rm -rf venv
```

---

**That's it! You're ready to build with PersonalMem! 🚀**

