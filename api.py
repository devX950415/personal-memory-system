"""
PersonalMem API - Frontend-friendly redesign

Five endpoints. Every mutation returns the full updated user state so the
frontend can `setState(response)` without a refetch.

  GET    /users/{user_id}            -> full user state
  POST   /users/{user_id}/messages   -> LLM extract + state + extracted_memories
  PATCH  /users/{user_id}            -> direct mutation + state + changes
  DELETE /users/{user_id}            -> wipe + empty state
  GET    /health                     -> liveness
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import time

from memory_service import MemoryService
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PersonalMem API",
    description="Personal memory management - frontend-friendly API",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    memory_service: Optional[MemoryService] = MemoryService()
    logger.info("MemoryService initialized successfully")
except Exception as e:
    logger.warning(f"MemoryService initialization deferred (DB not yet available): {e}")
    memory_service = None

# ---------- Models ----------

class MessageRequest(BaseModel):
    message: str = Field(..., description="User message to extract personal info from")


class PatchRequest(BaseModel):
    action: str = Field(..., description="set | append | remove | delete | bulk_set")
    field: Optional[str] = None
    value: Optional[Any] = None
    values: Optional[Dict[str, Any]] = None


class UserState(BaseModel):
    user_id: str
    memories: Dict[str, Any]
    context_text: str
    has_memories: bool
    field_count: int
    created_at: Optional[float]
    updated_at: Optional[float]


class MessageResponse(UserState):
    extracted_memories: List[Dict[str, Any]]
    response_time_ms: int


class PatchResponse(UserState):
    changes: List[Dict[str, Any]]


# ---------- Helpers ----------

VALID_ACTIONS = {"set", "append", "remove", "delete", "bulk_set"}


def _require_db():
    if memory_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available. Ensure MongoDB is running.",
        )


def _build_user_state(user_id: str) -> Dict[str, Any]:
    record = memory_service.get_user_record(user_id)
    if not record:
        return {
            "user_id": user_id,
            "memories": {},
            "context_text": "",
            "has_memories": False,
            "field_count": 0,
            "created_at": None,
            "updated_at": None,
        }

    memories = record.get("memories", {}) or {}
    if memories:
        lines = ["User Information:"]
        for key, val in memories.items():
            val_str = ", ".join(str(v) for v in val) if isinstance(val, list) else str(val)
            lines.append(f"- {key}: {val_str}")
        context_text = "\n".join(lines)
    else:
        context_text = ""

    return {
        "user_id": user_id,
        "memories": memories,
        "context_text": context_text,
        "has_memories": bool(memories),
        "field_count": len(memories),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def _validate_patch(req: PatchRequest):
    if req.action not in VALID_ACTIONS:
        raise HTTPException(400, f"Unknown action '{req.action}'. Use one of: {sorted(VALID_ACTIONS)}")
    if req.action in {"set", "append", "remove", "delete"} and not req.field:
        raise HTTPException(400, f"Action '{req.action}' requires 'field'")
    if req.action in {"set", "append", "remove"} and req.value is None:
        raise HTTPException(400, f"Action '{req.action}' requires 'value'")
    if req.action == "bulk_set" and (not isinstance(req.values, dict) or not req.values):
        raise HTTPException(400, "Action 'bulk_set' requires non-empty 'values' dict")


# ---------- Endpoints ----------

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "PersonalMem API",
    }


@app.get("/users/{user_id}", response_model=UserState)
async def get_user(user_id: str):
    """Load the full user state - everything the frontend needs in one call."""
    _require_db()
    try:
        return _build_user_state(user_id)
    except ConnectionError as e:
        raise HTTPException(503, f"Database unavailable: {e}")
    except Exception as e:
        raise HTTPException(500, f"Error loading user: {e}")


@app.post("/users/{user_id}/messages", response_model=MessageResponse)
async def extract_from_message(user_id: str, request: MessageRequest):
    """LLM-extract memories from a sentence. Returns updated user state + what was extracted."""
    _require_db()
    start = time.time()
    try:
        extracted = memory_service.add_memory_from_message(user_id, request.message)
        state = _build_user_state(user_id)
        return {
            **state,
            "extracted_memories": extracted,
            "response_time_ms": int((time.time() - start) * 1000),
        }
    except ConnectionError as e:
        raise HTTPException(503, f"Database unavailable: {e}")
    except Exception as e:
        raise HTTPException(500, f"Error processing message: {e}")


@app.patch("/users/{user_id}", response_model=PatchResponse)
async def patch_user(user_id: str, request: PatchRequest):
    """Direct mutation via action verb. Returns updated user state + change records."""
    _require_db()
    _validate_patch(request)
    try:
        changes = memory_service.apply_action(
            user_id=user_id,
            action=request.action,
            field=request.field,
            value=request.value,
            values=request.values,
        )
        state = _build_user_state(user_id)
        return {**state, "changes": changes}
    except ConnectionError as e:
        raise HTTPException(503, f"Database unavailable: {e}")
    except Exception as e:
        raise HTTPException(500, f"Error applying patch: {e}")


@app.delete("/users/{user_id}", response_model=UserState)
async def delete_user(user_id: str):
    """Wipe the user. Returns the empty post-delete state."""
    _require_db()
    try:
        memory_service.delete_all_memories(user_id)
        return _build_user_state(user_id)
    except ConnectionError as e:
        raise HTTPException(503, f"Database unavailable: {e}")
    except Exception as e:
        raise HTTPException(500, f"Error deleting user: {e}")


if __name__ == "__main__":
    import uvicorn

    config.validate()
    uvicorn.run("api:app", host="0.0.0.0", port=8888, reload=True)
