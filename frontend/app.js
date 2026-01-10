// PersonalMem Frontend - Memory Only Version

const API_URL = 'http://localhost:8888';
let USER_ID = 'test_user';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    USER_ID = document.getElementById('userId').value;
    testConnection();
});

function getApiUrl() {
    return document.getElementById('apiUrl').value || API_URL;
}

function getUserId() {
    return document.getElementById('userId').value || USER_ID;
}

function showStatus(message, type = 'info') {
    const statusBar = document.getElementById('statusBar');
    statusBar.textContent = message;
    statusBar.className = `status-bar show ${type}`;
    
    setTimeout(() => {
        statusBar.classList.remove('show');
    }, 3000);
}

async function testConnection() {
    try {
        const response = await fetch(`${getApiUrl()}/health`);
        if (response.ok) {
            showStatus('✅ API connection successful', 'success');
        } else {
            showStatus('❌ API connection failed', 'error');
        }
    } catch (error) {
        showStatus('❌ Cannot connect to API', 'error');
    }
}

async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    
    if (!message) {
        showStatus('Please enter a message', 'error');
        return;
    }
    
    const userId = getUserId();
    if (!userId) {
        showStatus('Please enter a user ID', 'error');
        return;
    }
    
    showStatus('Processing message...', 'info');
    
    try {
        const response = await fetch(`${getApiUrl()}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                message: message
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Display response
        displayResponse(message, data);
        
        // Clear input
        messageInput.value = '';
        
        // Show status
        if (data.extracted_memories && data.extracted_memories.length > 0) {
            showStatus(`✅ Extracted ${data.extracted_memories.length} memories`, 'success');
            loadMemories(); // Refresh memories
        } else {
            showStatus('✅ Message processed (no personal info)', 'success');
        }
        
    } catch (error) {
        showStatus(`❌ Error: ${error.message}`, 'error');
    }
}

function displayResponse(message, data) {
    const responseArea = document.getElementById('responseArea');
    
    const responseDiv = document.createElement('div');
    responseDiv.className = 'response-item';
    
    let html = `<div class="response-message"><strong>Message:</strong> ${escapeHtml(message)}</div>`;
    
    if (data.extracted_memories && data.extracted_memories.length > 0) {
        html += '<div class="response-memories"><strong>Extracted:</strong><ul>';
        data.extracted_memories.forEach(mem => {
            html += `<li>${escapeHtml(mem.memory || JSON.stringify(mem))}</li>`;
        });
        html += '</ul></div>';
    }
    
    if (data.memory_context) {
        html += `<div class="response-context"><strong>Context:</strong><pre>${escapeHtml(data.memory_context)}</pre></div>`;
    }
    
    responseDiv.innerHTML = html;
    responseArea.insertBefore(responseDiv, responseArea.firstChild);
    
    // Keep only last 5 responses
    while (responseArea.children.length > 5) {
        responseArea.removeChild(responseArea.lastChild);
    }
}

async function loadMemories() {
    const userId = getUserId();
    if (!userId) {
        showStatus('Please enter a user ID', 'error');
        return;
    }
    
    showStatus('Loading memories...', 'info');
    
    try {
        const response = await fetch(`${getApiUrl()}/users/${userId}/memories`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const memories = await response.json();
        displayMemories(memories);
        showStatus(`✅ Loaded ${memories.length} memories`, 'success');
        
    } catch (error) {
        showStatus(`❌ Error loading memories: ${error.message}`, 'error');
    }
}

function displayMemories(memories) {
    const memoriesList = document.getElementById('memoriesList');
    memoriesList.innerHTML = '';
    
    if (memories.length === 0) {
        memoriesList.innerHTML = '<div class="info-text">No memories stored yet</div>';
        return;
    }
    
    memories.forEach(mem => {
        const memDiv = document.createElement('div');
        memDiv.className = 'memory-item';
        
        let html = `<strong>${escapeHtml(mem.memory)}</strong>`;
        
        if (mem.created_at) {
            html += `<div class="memory-meta">Created: ${new Date(mem.created_at).toLocaleString()}</div>`;
        }
        
        memDiv.innerHTML = html;
        memoriesList.appendChild(memDiv);
    });
}

async function clearAllMemories() {
    const userId = getUserId();
    if (!userId) {
        showStatus('Please enter a user ID', 'error');
        return;
    }
    
    if (!confirm('Are you sure you want to delete ALL memories? This cannot be undone.')) {
        return;
    }
    
    showStatus('Deleting memories...', 'info');
    
    try {
        const response = await fetch(`${getApiUrl()}/users/${userId}/memories`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        showStatus('✅ All memories deleted', 'success');
        loadMemories();
        
    } catch (error) {
        showStatus(`❌ Error deleting memories: ${error.message}`, 'error');
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
