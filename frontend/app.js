// PersonalMem Frontend - Memory Only Version

const API_URL = 'http://localhost:8888';
let USER_ID = 'test_user';

// Initialize is now handled at the bottom of the file

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
            showStatus('API connection successful', 'success');
            return true;
        } else {
            showStatus('API connection failed', 'error');
            return false;
        }
    } catch (error) {
        showStatus('Cannot connect to API. Make sure the server is running.', 'error');
        return false;
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
    
    const startTime = performance.now();
    
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
        
        const responseTime = Math.round(performance.now() - startTime);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Display response with timing
        displayResponse(message, data, responseTime);
        
        // Clear input
        messageInput.value = '';
        
        // Show status with timing
        if (data.extracted_memories && data.extracted_memories.length > 0) {
            const addedCount = data.extracted_memories.filter(m => m.event !== 'REMOVE').length;
            const removedCount = data.extracted_memories.filter(m => m.event === 'REMOVE').length;
            
            let statusMsg = 'Memory updated: ';
            if (addedCount > 0) statusMsg += `${addedCount} added`;
            if (addedCount > 0 && removedCount > 0) statusMsg += ', ';
            if (removedCount > 0) statusMsg += `${removedCount} removed`;
            statusMsg += ` (${responseTime}ms)`;
            
            showStatus(statusMsg, 'success');
            loadMemories(); // Refresh memories
        } else {
            showStatus(`Message processed (no personal info) (${responseTime}ms)`, 'success');
        }
        
    } catch (error) {
        const responseTime = Math.round(performance.now() - startTime);
        showStatus(`Error: ${error.message} (${responseTime}ms)`, 'error');
    }
}

function displayResponse(message, data, responseTime) {
    const responseArea = document.getElementById('responseArea');
    
    // Clear placeholder if it exists
    const placeholder = responseArea.querySelector('.info-text');
    if (placeholder) {
        placeholder.remove();
    }
    
    const responseDiv = document.createElement('div');
    responseDiv.className = 'response-item';
    
    let html = `<div class="response-message"><strong>Your Message:</strong> "${escapeHtml(message)}" <span class="response-time">(${responseTime}ms)</span></div>`;
    
    if (data.extracted_memories && data.extracted_memories.length > 0) {
        const additions = data.extracted_memories.filter(m => m.event !== 'REMOVE');
        const removals = data.extracted_memories.filter(m => m.event === 'REMOVE');
        
        html += '<div class="response-memories"><strong>Memory Changes:</strong>';
        
        if (additions.length > 0) {
            html += '<div class="memory-section"><strong>Added/Updated:</strong><ul>';
            additions.forEach(mem => {
                const field = mem.field || mem.key || 'unknown';
                let value = mem.value || '';
                if (Array.isArray(value)) {
                    value = value.join(', ');
                }
                const event = mem.event || 'ADDED';
                html += `<li><span class="memory-field">${escapeHtml(field)}</span>: <span class="memory-value">${escapeHtml(String(value))}</span> <span class="memory-event added">(${event})</span></li>`;
            });
            html += '</ul></div>';
        }
        
        if (removals.length > 0) {
            html += '<div class="memory-section"><strong>Removed:</strong><ul>';
            removals.forEach(mem => {
                const field = mem.field || mem.key || 'unknown';
                let value = mem.value || '';
                if (Array.isArray(value)) {
                    value = value.join(', ');
                }
                html += `<li><span class="memory-field">${escapeHtml(field)}</span>: <span class="memory-value removed">${escapeHtml(String(value))}</span> <span class="memory-event removed">(REMOVED)</span></li>`;
            });
            html += '</ul></div>';
        }
        
        html += '</div>';
    } else {
        html += '<div class="response-info">No personal information extracted from this message.</div>';
    }
    
    if (data.memory_context && data.memory_context.trim()) {
        html += `<div class="response-context"><strong>Current Memory Context:</strong><pre>${escapeHtml(data.memory_context)}</pre></div>`;
    }
    
    responseDiv.innerHTML = html;
    responseArea.insertBefore(responseDiv, responseArea.firstChild);
    
    // Keep only last 10 responses
    while (responseArea.children.length > 10) {
        responseArea.removeChild(responseArea.lastChild);
    }
    
    // Auto-scroll to top
    responseArea.scrollTop = 0;
}

async function loadMemories() {
    const userId = getUserId();
    if (!userId) {
        showStatus('Please enter a user ID', 'error');
        return;
    }
    
    showStatus('Loading memories...', 'info');
    
    const startTime = performance.now();
    
    try {
        const response = await fetch(`${getApiUrl()}/users/${userId}/memories/raw`);
        
        const responseTime = Math.round(performance.now() - startTime);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        displayMemories(data.memories);
        const count = Object.keys(data.memories).length;
        showStatus(`Loaded ${count} memory fields (${responseTime}ms)`, 'success');
        
    } catch (error) {
        const responseTime = Math.round(performance.now() - startTime);
        showStatus(`Error loading memories: ${error.message} (${responseTime}ms)`, 'error');
    }
}

function displayMemories(memories) {
    const memoriesList = document.getElementById('memoriesList');
    memoriesList.innerHTML = '';
    
    if (!memories || Object.keys(memories).length === 0) {
        memoriesList.innerHTML = '<div class="info-text">No memories stored yet.<br>Send a message with personal information to create memories.</div>';
        return;
    }
    
    for (const [key, value] of Object.entries(memories)) {
        const memDiv = document.createElement('div');
        memDiv.className = 'memory-item';
        
        let valueStr = value;
        if (Array.isArray(value)) {
            valueStr = value.join(', ');
        }
        
        let html = `<div class="memory-header">
            <span class="memory-content"><strong>${escapeHtml(key)}:</strong> ${escapeHtml(String(valueStr))}</span>
        </div>`;
        
        memDiv.innerHTML = html;
        memoriesList.appendChild(memDiv);
    }
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
        
        showStatus('All memories deleted', 'success');
        loadMemories();
        
    } catch (error) {
        showStatus(`Error deleting memories: ${error.message}`, 'error');
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

// Auto-load memories on page load
document.addEventListener('DOMContentLoaded', async () => {
    USER_ID = document.getElementById('userId').value;
    const userIdInput = document.getElementById('userId');
    
    // Update USER_ID when input changes
    userIdInput.addEventListener('change', () => {
        USER_ID = userIdInput.value;
        if (USER_ID) {
            loadMemories();
        }
    });
    
    // Test connection and load memories on initialization
    await testConnection();
    if (getUserId()) {
        loadMemories();
    }
});
