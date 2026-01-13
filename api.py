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
import time

from app import PersonalMemApp
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PersonalMem API",
    description="Personalized User Memory System - Memory Only",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    personal_mem_app = PersonalMemApp()
    logger.info("PersonalMemApp initialized successfully")
except Exception as e:
    logger.warning(f"PersonalMemApp initialization deferred (DB not yet available): {e}")
    personal_mem_app = None

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", include_in_schema=False)
async def redirect_to_frontend():
    return RedirectResponse(url="/static/index.html")


class SendMessageRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    message: str = Field(..., description="User message")


class SendMessageResponse(BaseModel):
    success: bool
    memory_context: str
    extracted_memories: List[Dict[str, Any]]
    message: str = "Message processed successfully"
    response_time_ms: Optional[int] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "PersonalMem API"
    }


@app.post("/messages", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """
    Process a user message.
    
    Memory extraction is automatic - the LLM analyzes every message to determine
    if it contains long-term personal information (name, preferences, etc).
    """
    start_time = time.time()
    
    if personal_mem_app is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available. Please ensure MongoDB is running."
        )
    
    try:
        result = personal_mem_app.process_user_message(
            user_id=request.user_id,
            message=request.message
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return SendMessageResponse(
            success=True,
            memory_context=result['memory_context'],
            extracted_memories=result['extracted_memories'],
            response_time_ms=response_time_ms
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to MongoDB. Please ensure MongoDB is running. Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@app.get("/users/{user_id}/memories/raw")
async def get_raw_memories(user_id: str):
    """
    Get raw memories as JSON object (for backend integration).
    Returns the memories directly as key-value pairs without formatting.
    """
    if personal_mem_app is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available."
        )
    
    try:
        memories = personal_mem_app.memory_service.get_user_memories(user_id)
        return {
            "user_id": user_id,
            "memories": memories
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving memories: {str(e)}"
        )


@app.get("/users/{user_id}/context/text")
async def get_user_context_text(user_id: str):
    """
    Get user context as plain text for chatbot prompts.
    Returns formatted string ready to inject into system prompt.
    """
    if personal_mem_app is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available."
        )
    
    try:
        memories = personal_mem_app.memory_service.get_user_memories(user_id)
        
        if not memories:
            return {
                "user_id": user_id,
                "context": "",
                "has_memories": False
            }
        
        # Format as readable text for LLM prompt
        context_lines = ["User Information:"]
        for key, value in memories.items():
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            else:
                value_str = str(value)
            context_lines.append(f"- {key}: {value_str}")
        
        return {
            "user_id": user_id,
            "context": "\n".join(context_lines),
            "has_memories": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving context: {str(e)}"
        )


@app.post("/users/{user_id}/memories/batch")
async def batch_update_memories(user_id: str, memories: Dict[str, Any]):
    """
    Batch update memories directly (for backend integration).
    Useful when you want to set memories programmatically.
    """
    if personal_mem_app is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available."
        )
    
    try:
        # Get current memories
        current = personal_mem_app.memory_service.get_user_memories(user_id)
        
        # Merge with new memories
        updated = {**current, **memories}
        
        # Save
        personal_mem_app.memory_service._save_memories(user_id, updated)
        
        return {
            "success": True,
            "user_id": user_id,
            "updated_fields": list(memories.keys()),
            "total_fields": len(updated)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating memories: {str(e)}"
        )


@app.delete("/users/{user_id}/memories")
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


if __name__ == "__main__":
    import uvicorn
    
    config.validate()
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8888,
        reload=True
    )
