"""
PersonalMem API

REST API for personal memory management.
No chat history - only user personal memories.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app import PersonalMemApp
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app_api = FastAPI(
    title="PersonalMem API",
    description="Personalized User Memory System - Memory Only",
    version="2.0.0"
)

app_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize PersonalMem app (lazy - will connect to DB on first use)
try:
    personal_mem_app = PersonalMemApp()
    logger.info("PersonalMemApp initialized successfully")
except Exception as e:
    logger.warning(f"PersonalMemApp initialization deferred (DB not yet available): {e}")
    personal_mem_app = None

# Mount static files for the frontend
app_api.mount("/static", StaticFiles(directory="frontend"), name="static")

@app_api.get("/", include_in_schema=False)
async def redirect_to_frontend():
    return RedirectResponse(url="/static/index.html")


# ============================================================================
# Request/Response Models
# ============================================================================

class SendMessageRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    message: str = Field(..., description="User message")


class SendMessageResponse(BaseModel):
    success: bool
    memory_context: str
    extracted_memories: List[Dict[str, Any]]
    message: str = "Message processed successfully"


class MemoryInfo(BaseModel):
    id: str
    memory: str
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ============================================================================
# Health Check
# ============================================================================

@app_api.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "PersonalMem API"
    }


# ============================================================================
# Message Processing
# ============================================================================

@app_api.post("/messages", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """
    Process a user message.
    
    Memory extraction is automatic - the LLM analyzes every message to determine
    if it contains long-term personal information (name, preferences, etc).
    """
    if personal_mem_app is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available. Please ensure PostgreSQL is running."
        )
    
    try:
        result = personal_mem_app.process_user_message(
            user_id=request.user_id,
            message=request.message
        )
        
        return SendMessageResponse(
            success=True,
            memory_context=result['memory_context'],
            extracted_memories=result['extracted_memories']
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to PostgreSQL. Please ensure PostgreSQL is running. Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


# ============================================================================
# Memory Management
# ============================================================================

@app_api.get("/users/{user_id}/memories", response_model=List[MemoryInfo])
async def get_user_memories(user_id: str):
    """Get all memories for a user"""
    if personal_mem_app is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available. Please ensure PostgreSQL is running."
        )
    
    try:
        memories = personal_mem_app.get_all_user_memories(user_id)
        
        return [
            MemoryInfo(
                id=mem.get('id', ''),
                memory=mem.get('memory', ''),
                user_id=mem.get('user_id'),
                created_at=mem.get('created_at'),
                updated_at=mem.get('updated_at')
            )
            for mem in memories
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving memories: {str(e)}"
        )


@app_api.get("/users/{user_id}/memories/search")
async def search_memories(user_id: str, query: str, limit: int = 5):
    """Search user memories with semantic similarity"""
    try:
        memories = personal_mem_app.search_user_memories(user_id, query, limit)
        
        return [
            MemoryInfo(
                id=mem.get('id', ''),
                memory=mem.get('memory', ''),
                user_id=mem.get('user_id'),
                created_at=mem.get('created_at'),
                updated_at=mem.get('updated_at')
            )
            for mem in memories
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching memories: {str(e)}"
        )


@app_api.delete("/users/{user_id}/memories")
async def delete_all_memories(user_id: str):
    """Delete all memories for a user"""
    try:
        success = personal_mem_app.delete_all_user_memories(user_id)
        
        if success:
            return {"message": f"All memories deleted for user {user_id}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete memories"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting memories: {str(e)}"
        )


@app_api.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a specific memory"""
    try:
        success = personal_mem_app.delete_user_memory(memory_id)
        
        if success:
            return {"message": f"Memory {memory_id} deleted"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting memory: {str(e)}"
        )


# ============================================================================
# Context Retrieval
# ============================================================================

@app_api.get("/users/{user_id}/context")
async def get_user_context(user_id: str):
    """Get complete context for a user (all memories)"""
    try:
        context = personal_mem_app.get_user_context(user_id)
        return context
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving context: {str(e)}"
        )


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    config.validate()
    
    uvicorn.run(
        "api:app_api",
        host="0.0.0.0",
        port=8888,
        reload=True
    )
