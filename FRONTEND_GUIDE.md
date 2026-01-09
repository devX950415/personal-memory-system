# Frontend Testing Guide

## Quick Start

### Option 1: Access via API Server (Easiest)

1. **Start the API server:**
   ```bash
   python api.py
   ```

2. **Open your browser:**
   - Visit: **http://localhost:8888/**
   - The frontend will be served automatically!

### Option 2: Standalone Frontend

1. **Start the API server:**
   ```bash
   python api.py
   ```

2. **Serve the frontend:**
   ```bash
   cd frontend
   python3 -m http.server 8080
   ```

3. **Open your browser:**
   - Visit: **http://localhost:8080**

## Features

### 🎯 Main Features

1. **Chat Management**
   - Create new chat sessions
   - View all your chats
   - Switch between chats

2. **Message Sending**
   - Send messages with memory extraction
   - View conversation history
   - Real-time message display

3. **Memory Management**
   - View all stored memories
   - See memory details and timestamps
   - Clear all memories (with confirmation)

4. **Configuration**
   - Set API URL
   - Set User ID
   - Test API connection

## Testing Workflow

### Step 1: Test Connection
1. Open the frontend
2. Click "Test Connection"
3. Should see: ✅ Connected to API successfully!

### Step 2: Create a Chat
1. Enter a chat title (e.g., "My First Chat")
2. Click "Create New Chat"
3. Chat should appear in the info box

### Step 3: Send Messages
1. Type a message: "My name is Alice and I love Python"
2. Make sure "Extract Memory" is checked
3. Click "Send" or press Enter
4. Message should appear in the chat

### Step 4: View Memories
1. Click "Refresh Memories"
2. You should see extracted memories like:
   - "User's name is Alice"
   - "User loves Python"

### Step 5: Test Memory Persistence
1. Create a new chat
2. Ask: "What is my name?"
3. The system should retrieve memories from the previous chat

## Example Test Scenarios

### Scenario 1: Basic Memory Extraction
```
1. Create chat: "Introduction"
2. Send: "My name is Bob. I'm a software engineer."
3. Check memories - should see:
   - "User's name is Bob"
   - "User is a software engineer"
```

### Scenario 2: Memory Persistence
```
1. Create chat: "Chat A"
2. Send: "My favorite language is JavaScript"
3. Create new chat: "Chat B"
4. Send: "What programming language do I like?"
5. System should remember: JavaScript
```

### Scenario 3: Task-Specific Filtering
```
1. Create chat: "Debugging"
2. Send: "Help me fix this bug: def add(a,b): return a-b"
3. Check memories - should NOT store this (task-specific)
```

## Troubleshooting

### Connection Issues
- **Error: Connection failed**
  - Make sure API is running: `python api.py`
  - Check API URL is correct (default: http://localhost:8888)
  - Check browser console for CORS errors

### Memory Not Showing
- **No memories extracted**
  - Make sure "Extract Memory" checkbox is checked
  - Check API logs for errors
  - Try sending a clear personal statement: "My name is John"

### Messages Not Sending
- **Error when sending message**
  - Make sure a chat is created/selected
  - Check User ID is set correctly
  - Verify API is responding (test connection)

### CORS Errors
- If accessing from different origin, the API already has CORS enabled
- If issues persist, check browser console for specific errors

## Browser Console

Open browser developer tools (F12) to see:
- API requests and responses
- JavaScript errors
- Network issues

## API Endpoints Tested

The frontend tests these endpoints:
- ✅ `GET /health` - Connection test
- ✅ `POST /chats` - Create chat
- ✅ `GET /users/{user_id}/chats` - List chats
- ✅ `GET /chats/{chat_id}/messages` - Get messages
- ✅ `POST /chats/messages` - Send message
- ✅ `GET /users/{user_id}/memories` - Get memories
- ✅ `DELETE /users/{user_id}/memories` - Delete memories

## Tips

1. **Use different User IDs** to test isolation
2. **Check API logs** to see what's happening server-side
3. **Use browser DevTools** to inspect API calls
4. **Test memory extraction** with clear personal statements
5. **Verify chat isolation** by creating multiple chats

## Next Steps

After testing with the frontend:
- Integrate with your actual application
- Customize the UI for your needs
- Add authentication if needed
- Deploy to production

---

**Happy Testing! 🚀**

