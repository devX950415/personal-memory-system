"""
FastAPI REST API for PersonalMem System
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app import PersonalMemApp
from config import config

# Initialize FastAPI app
app_api = FastAPI(
    title="PersonalMem API",
    description="Personalized User Memory System with isolated chat history",
    version="1.0.0"
)

# Add CORS middleware
app_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize PersonalMem app
personal_mem_app = PersonalMemApp()


# ==================== Request/Response Models ====================

class CreateChatRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    title: Optional[str] = Field(None, description="Chat title")


class CreateChatResponse(BaseModel):
    chat_id: str
    user_id: str
    title: str
    created_at: datetime


class SendMessageRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    chat_id: str = Field(..., description="Chat ID")
    message: str = Field(..., description="User message")
    extract_memory: bool = Field(True, description="Whether to extract memories")


class SendMessageResponse(BaseModel):
    success: bool
    chat_id: str
    memory_context: str
    extracted_memories: List[Dict[str, Any]]
    message: str = "Message processed successfully"


class AssistantResponseRequest(BaseModel):
    chat_id: str = Field(..., description="Chat ID")
    response: str = Field(..., description="Assistant response")


class MemoryItem(BaseModel):
    id: str
    memory: str
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChatInfo(BaseModel):
    chat_id: str
    title: str
    created_at: datetime
    message_count: int


class MessageInfo(BaseModel):
    role: str
    content: str
    timestamp: datetime


# ==================== Chat Endpoints ====================

@app_api.post("/chats", response_model=CreateChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(request: CreateChatRequest):
    """Create a new chat session"""
    try:
        chat_id = personal_mem_app.create_new_chat(
            user_id=request.user_id,
            title=request.title
        )
        
        chat = personal_mem_app.chat_service.get_chat(chat_id)
        
        return CreateChatResponse(
            chat_id=chat.chat_id,
            user_id=chat.user_id,
            title=chat.title,
            created_at=chat.created_at
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating chat: {str(e)}"
        )


@app_api.get("/users/{user_id}/chats", response_model=List[ChatInfo])
async def get_user_chats(user_id: str):
    """Get all chats for a user"""
    try:
        chats = personal_mem_app.get_user_chats(user_id)
        return chats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving chats: {str(e)}"
        )


@app_api.get("/chats/{chat_id}/messages", response_model=List[MessageInfo])
async def get_chat_messages(chat_id: str):
    """Get all messages in a chat"""
    try:
        messages = personal_mem_app.chat_service.get_chat_history(chat_id)
        
        if messages is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        return [
            MessageInfo(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp
            )
            for msg in messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving messages: {str(e)}"
        )


@app_api.post("/chats/messages", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """Send a user message and process it"""
    try:
        result = personal_mem_app.process_user_message(
            user_id=request.user_id,
            chat_id=request.chat_id,
            message=request.message,
            extract_memory=request.extract_memory
        )
        
        return SendMessageResponse(
            success=True,
            chat_id=request.chat_id,
            memory_context=result['memory_context'],
            extracted_memories=result['extracted_memories']
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@app_api.post("/chats/responses")
async def add_assistant_response(request: AssistantResponseRequest):
    """Add an assistant response to a chat"""
    try:
        success = personal_mem_app.add_assistant_response(
            chat_id=request.chat_id,
            response=request.response
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        return {"success": True, "message": "Response added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding response: {str(e)}"
        )


@app_api.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat and all its messages"""
    try:
        success = personal_mem_app.delete_chat(chat_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        return {"success": True, "message": "Chat deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting chat: {str(e)}"
        )


# ==================== Memory Endpoints ====================

@app_api.get("/users/{user_id}/memories", response_model=List[MemoryItem])
async def get_user_memories(user_id: str):
    """Get all personal memories for a user"""
    try:
        memories = personal_mem_app.get_all_user_memories(user_id)
        
        return [
            MemoryItem(
                id=mem.get('id', ''),
                memory=mem.get('memory', ''),
                user_id=user_id,
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


@app_api.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a specific memory"""
    try:
        success = personal_mem_app.delete_user_memory(memory_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )
        
        return {"success": True, "message": "Memory deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting memory: {str(e)}"
        )


@app_api.delete("/users/{user_id}/memories")
async def delete_all_user_memories(user_id: str):
    """Delete all memories for a user (memory opt-out)"""
    try:
        success = personal_mem_app.delete_all_user_memories(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error deleting memories"
            )
        
        return {"success": True, "message": "All memories deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting memories: {str(e)}"
        )


@app_api.get("/users/{user_id}/context/{chat_id}")
async def get_user_context(user_id: str, chat_id: str):
    """Get complete context (memories + chat history) for generating responses"""
    try:
        context = personal_mem_app.get_user_context(user_id, chat_id)
        
        return {
            "user_id": user_id,
            "chat_id": chat_id,
            "context": context
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving context: {str(e)}"
        )


# ==================== Health Check ====================

@app_api.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PersonalMem API",
        "version": "1.0.0"
    }


# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn
    
    try:
        config.validate()
        uvicorn.run(
            "api:app_api",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level=config.LOG_LEVEL.lower()
        )
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease create a .env file with required settings.")

