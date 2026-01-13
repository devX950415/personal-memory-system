"""
Configuration management for PersonalMem
"""
import os
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://admin:admin123@localhost:27017/")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "personalmem")
    
    AZURE_OPENAI_API_KEY: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    AZURE_OPENAI_MODEL: Optional[str] = os.getenv("AZURE_OPENAI_MODEL")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
    
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def get_log_level(cls) -> int:
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(cls.LOG_LEVEL.upper(), logging.INFO)
    
    @classmethod
    def is_azure_openai(cls) -> bool:
        return all([
            cls.AZURE_OPENAI_API_KEY,
            cls.AZURE_OPENAI_ENDPOINT,
            cls.AZURE_OPENAI_DEPLOYMENT,
            cls.AZURE_OPENAI_MODEL,
        ])
    
    @classmethod
    def validate(cls) -> None:
        if cls.is_azure_openai():
            if not cls.AZURE_OPENAI_API_KEY:
                raise ValueError("AZURE_OPENAI_API_KEY is required for Azure OpenAI.")
            if not cls.AZURE_OPENAI_ENDPOINT:
                raise ValueError("AZURE_OPENAI_ENDPOINT is required for Azure OpenAI.")
            if not cls.AZURE_OPENAI_DEPLOYMENT:
                raise ValueError("AZURE_OPENAI_DEPLOYMENT is required for Azure OpenAI.")
            if not cls.AZURE_OPENAI_MODEL:
                raise ValueError("AZURE_OPENAI_MODEL is required for Azure OpenAI.")
        elif not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required if not using Azure OpenAI.")
        
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI is required.")
        if not cls.MONGODB_DATABASE:
            raise ValueError("MONGODB_DATABASE is required.")


config = Config()
