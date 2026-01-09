# PersonalMem Frontend

A simple web interface to test the PersonalMem API.

## Features

- ✅ Create and manage chat sessions
- ✅ Send messages with **automatic** memory extraction
- ✅ View user memories
- ✅ Test API connectivity
- ✅ Clean, modern UI
- ✅ AI automatically detects personal information

## Usage

### Option 1: Open Directly

1. Make sure the API server is running:
   ```bash
   python api.py
   ```

2. Open `index.html` in your browser:
   ```bash
   # Using Python's built-in server
   cd frontend
   python3 -m http.server 8080
   ```
   
   Then visit: http://localhost:8080

### Option 2: Serve with API (Recommended)

The API server can serve the frontend. Update `api.py` to include static file serving, or use a simple HTTP server.

## Quick Start

1. **Start the API:**
   ```bash
   python api.py
   ```

2. **Open the frontend:**
   - Open `frontend/index.html` in your browser
   - Or serve it with: `cd frontend && python3 -m http.server 8080`

3. **Configure:**
   - Set API URL (default: http://localhost:8888)
   - Set User ID (default: test_user)

4. **Test:**
   - Click "Test Connection" to verify API is running
   - Create a new chat
   - Send messages
   - View extracted memories

## Features Explained

### Chat Management
- **Create New Chat**: Start a new conversation
- **Load My Chats**: View all your existing chats
- Click on a chat to load its messages

### Chat Interface
- Type messages and send
- **Memory extraction is automatic** - the AI analyzes every message
- Personal information is detected and stored automatically
- Messages are displayed in real-time

### Memories Panel
- **Refresh Memories**: Load all stored memories
- **Clear All Memories**: Delete all memories (with confirmation)
- View memory details and timestamps

## API Endpoints Used

- `GET /health` - Test connection
- `POST /chats` - Create chat
- `GET /users/{user_id}/chats` - List chats
- `GET /chats/{chat_id}/messages` - Get messages
- `POST /chats/messages` - Send message
- `GET /users/{user_id}/memories` - Get memories
- `DELETE /users/{user_id}/memories` - Delete all memories

## Browser Compatibility

Works in all modern browsers:
- Chrome/Edge (recommended)
- Firefox
- Safari

## Troubleshooting

**Connection Failed:**
- Make sure API server is running on the configured port
- Check CORS settings if accessing from different origin

**Messages Not Sending:**
- Verify chat is created/selected
- Check browser console for errors
- Ensure API is responding

**Memories Not Showing:**
- Memory extraction is automatic but only for personal information
- Try messages with clear personal info (name, preferences, etc.)
- Check API logs to see if memories were extracted
- Note: Not all messages contain extractable personal information

