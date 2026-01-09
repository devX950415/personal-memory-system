"""
Configuration management for PersonalMem system
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    
    # MongoDB settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "personalmem")
    
    # Azure OpenAI settings for LLM
    AZURE_OPENAI_API_KEY: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    AZURE_OPENAI_MODEL: Optional[str] = os.getenv("AZURE_OPENAI_MODEL")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
    
    # Azure OpenAI settings for Embeddings
    AZURE_OPENAI_EMBEDDING_API_KEY: Optional[str] = os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY")
    AZURE_OPENAI_EMBEDDING_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: Optional[str] = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    AZURE_OPENAI_EMBEDDING_MODEL: Optional[str] = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL")
    AZURE_OPENAI_EMBEDDING_API_VERSION: str = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION", "2024-12-01-preview")
    
    # Regular OpenAI settings (fallback, optional)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Application settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> None:
        """Validate that required configuration is present"""
        # Check if using Azure OpenAI or regular OpenAI
        if cls.AZURE_OPENAI_API_KEY and cls.AZURE_OPENAI_ENDPOINT:
            # Using Azure OpenAI
            if not cls.AZURE_OPENAI_DEPLOYMENT:
                raise ValueError(
                    "AZURE_OPENAI_DEPLOYMENT is required when using Azure OpenAI."
                )
            if not cls.AZURE_OPENAI_EMBEDDING_API_KEY or not cls.AZURE_OPENAI_EMBEDDING_ENDPOINT:
                raise ValueError(
                    "Azure OpenAI embedding credentials are required. "
                    "Please set AZURE_OPENAI_EMBEDDING_API_KEY and AZURE_OPENAI_EMBEDDING_ENDPOINT."
                )
        elif cls.OPENAI_API_KEY:
            # Using regular OpenAI
            pass
        else:
            raise ValueError(
                "Either Azure OpenAI credentials (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT) "
                "or OPENAI_API_KEY is required. Please set them in your .env file."
            )
        
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI is required.")
    
    @classmethod
    def is_azure_openai(cls) -> bool:
        """Check if using Azure OpenAI"""
        return bool(cls.AZURE_OPENAI_API_KEY and cls.AZURE_OPENAI_ENDPOINT)


config = Config()

