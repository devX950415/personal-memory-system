"""
PersonalMem Application

Main application logic focusing on:
- Personal memory management (per-user, persistent)
- Automatic memory extraction from user messages
"""

from typing import Dict, List, Any
import logging

from memory_service import MemoryService
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PersonalMemApp:
    
    def __init__(self):
        self.memory_service = MemoryService()
        logger.info("PersonalMemApp initialized")
    
    def process_user_message(self, user_id: str, message: str) -> Dict[str, Any]:
        extracted_memories = self.memory_service.add_memory_from_message(
            user_id=user_id,
            message=message
        )
        
        memory_context = self.memory_service.get_memory_context(user_id)
        
        return {
            "memory_context": memory_context,
            "extracted_memories": extracted_memories,
            "user_id": user_id
        }
    
    def delete_all_user_memories(self, user_id: str) -> bool:
        return self.memory_service.delete_all_memories(user_id)
