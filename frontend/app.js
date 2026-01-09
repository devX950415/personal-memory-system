// Configuration
let API_URL = 'http://localhost:8888';
let USER_ID = 'test_user';
let CURRENT_CHAT_ID = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    testConnection();
});

function loadConfig() {
    const apiUrl = localStorage.getItem('apiUrl') || 'http://localhost:8888';
    const userId = localStorage.getItem('userId') || 'test_user';
    
    document.getElementById('apiUrl').value = apiUrl;
    document.getElementById('userId').value = userId;
    
    API_URL = apiUrl;
    USER_ID = userId;
}

function saveConfig() {
    API_URL = document.getElementById('apiUrl').value;
    USER_ID = document.getElementById('userId').value;
    
    localStorage.setItem('apiUrl', API_URL);
    localStorage.setItem('userId', USER_ID);
}

async function testConnection() {
    saveConfig();
    showStatus('Testing connection...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();
        
        if (response.ok) {
            showStatus('✅ Connected to API successfully!', 'success');
        } else {
            showStatus('❌ API returned an error', 'error');
        }
    } catch (error) {
        showStatus(`❌ Connection failed: ${error.message}`, 'error');
    }
}

async function createChat() {
    saveConfig();
    const title = document.getElementById('chatTitle').value || 'New Chat';
    showStatus('Creating chat...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/chats`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: USER_ID,
                title: title
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        
        const data = await response.json();
        CURRENT_CHAT_ID = data.chat_id;
        
        document.getElementById('currentChatInfo').innerHTML = `
            <strong>Current Chat:</strong> ${data.title}<br>
            <small>Chat ID: ${data.chat_id}</small>
        `;
        
        clearChatMessages();
        addSystemMessage(`Chat "${data.title}" created!`);
        showStatus('✅ Chat created successfully!', 'success');
        loadUserChats();
    } catch (error) {
        showStatus(`❌ Failed to create chat: ${error.message}`, 'error');
    }
}

async function loadUserChats() {
    saveConfig();
    
    try {
        const response = await fetch(`${API_URL}/users/${USER_ID}/chats`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const chats = await response.json();
        
        if (chats.length > 0) {
            const chatInfo = document.getElementById('currentChatInfo');
            const chatList = chats.slice(0, 5).map(chat => 
                `<div style="margin: 5px 0; padding: 8px; background: #f0f0f0; border-radius: 4px; cursor: pointer;" 
                      onclick="selectChat('${chat.chat_id}', '${chat.title}')">
                    <strong>${chat.title}</strong> (${chat.message_count} messages)
                </div>`
            ).join('');
            
            chatInfo.innerHTML = `
                <strong>Your Chats:</strong><br>
                ${chatList}
            `;
        }
    } catch (error) {
        console.error('Error loading chats:', error);
    }
}

function selectChat(chatId, title) {
    CURRENT_CHAT_ID = chatId;
    document.getElementById('currentChatInfo').innerHTML = `
        <strong>Current Chat:</strong> ${title}<br>
        <small>Chat ID: ${chatId}</small>
    `;
    loadChatMessages(chatId);
    showStatus(`✅ Selected chat: ${title}`, 'success');
}

async function loadChatMessages(chatId) {
    try {
        const response = await fetch(`${API_URL}/chats/${chatId}/messages`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const messages = await response.json();
        clearChatMessages();
        
        if (messages.length === 0) {
            addSystemMessage('No messages in this chat yet.');
        } else {
            messages.forEach(msg => {
                addMessage(msg.role, msg.content);
            });
        }
    } catch (error) {
        showStatus(`❌ Failed to load messages: ${error.message}`, 'error');
    }
}

async function sendMessage() {
    if (!CURRENT_CHAT_ID) {
        showStatus('❌ Please create or select a chat first', 'error');
        return;
    }
    
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    
    if (!message) {
        return;
    }
    
    // Add user message to UI
    addMessage('user', message);
    messageInput.value = '';
    showStatus('Sending message (auto-analyzing for personal info)...', 'info');
    
    try {
        // Send message (memory extraction is automatic on backend)
        const response = await fetch(`${API_URL}/chats/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: USER_ID,
                chat_id: CURRENT_CHAT_ID,
                message: message
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        
        const data = await response.json();
        
        // Show extracted memories info
        if (data.extracted_memories && data.extracted_memories.length > 0) {
            showStatus(`✅ Message sent! Auto-extracted ${data.extracted_memories.length} personal memories`, 'success');
            loadMemories(); // Refresh memories
        } else {
            showStatus('✅ Message sent! (No personal info detected)', 'success');
        }
        
        // Simulate assistant response (you can replace this with actual API call)
        setTimeout(() => {
            addMessage('assistant', 'Message received and processed. Personal information automatically extracted if present.');
        }, 500);
        
    } catch (error) {
        showStatus(`❌ Failed to send message: ${error.message}`, 'error');
    }
}

async function loadMemories() {
    saveConfig();
    showStatus('Loading memories...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/users/${USER_ID}/memories`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const memories = await response.json();
        const memoriesList = document.getElementById('memoriesList');
        
        if (memories.length === 0) {
            memoriesList.innerHTML = '<div class="info-text">No memories stored yet.</div>';
        } else {
            memoriesList.innerHTML = memories.map((mem, index) => `
                <div class="memory-item">
                    <strong>Memory #${index + 1}</strong>
                    <div class="memory-text">${mem.memory || 'N/A'}</div>
                    <div class="memory-meta">
                        ID: ${mem.id} | 
                        ${mem.created_at ? `Created: ${new Date(mem.created_at).toLocaleString()}` : ''}
                    </div>
                </div>
            `).join('');
        }
        
        showStatus(`✅ Loaded ${memories.length} memories`, 'success');
    } catch (error) {
        showStatus(`❌ Failed to load memories: ${error.message}`, 'error');
        document.getElementById('memoriesList').innerHTML = 
            `<div class="info-text">Error: ${error.message}</div>`;
    }
}

async function clearAllMemories() {
    if (!confirm('Are you sure you want to delete ALL memories for this user?')) {
        return;
    }
    
    saveConfig();
    showStatus('Deleting all memories...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/users/${USER_ID}/memories`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        document.getElementById('memoriesList').innerHTML = 
            '<div class="info-text">All memories deleted.</div>';
        showStatus('✅ All memories deleted', 'success');
    } catch (error) {
        showStatus(`❌ Failed to delete memories: ${error.message}`, 'error');
    }
}

function addMessage(role, content) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.textContent = content;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addSystemMessage(content) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system';
    messageDiv.textContent = content;
    messagesDiv.appendChild(messageDiv);
}

function clearChatMessages() {
    document.getElementById('chatMessages').innerHTML = '';
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function showStatus(message, type = 'info') {
    const statusBar = document.getElementById('statusBar');
    statusBar.textContent = message;
    statusBar.className = `status-bar show ${type}`;
    
    setTimeout(() => {
        statusBar.classList.remove('show');
    }, 3000);
}

