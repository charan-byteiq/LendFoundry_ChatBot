"""
Centralized Gemini LLM Service

This module provides two ways to interact with Google's Gemini models:
1. GeminiClient - Direct Google GenAI SDK (for simple content generation, async support)
2. GeminiLangChain - LangChain wrapper (for agent workflows, chains, and tools)

Usage:
    # For direct content generation (sync/async)
    from services import get_gemini_client
    client = get_gemini_client()
    response = client.generate(prompt)
    response = await client.generate_async(prompt)
    
    # For LangChain-based workflows
    from services import get_langchain_llm, get_sql_generator_llm
    llm = get_langchain_llm()
    sql_llm = get_sql_generator_llm()  # With safety settings disabled
"""

import os
from typing import Optional, Any, Dict, List, Union
from dotenv import load_dotenv
from logger import logger

load_dotenv()

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.0

# Safety settings for SQL/code generation (disabled for technical content)
SAFETY_SETTINGS_DISABLED = {
    "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
}


def _get_api_key() -> str:
    """Get Gemini API key from environment variables."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Set GEMINI_API_KEY environment variable."
        )
    return api_key


# =============================================================================
# GeminiClient - Direct Google GenAI SDK
# =============================================================================

class GeminiClient:
    """
    Direct Google GenAI SDK client for simple content generation.
    
    Use this for:
    - Simple text generation
    - Async content generation
    - Multimodal content (PDF, images)
    - Classification tasks
    
    Examples:
        client = GeminiClient()
        
        # Sync generation
        response = client.generate("Explain machine learning")
        
        # Async generation
        response = await client.generate_async("Classify this query")
        
        # With PDF content
        from google.genai.types import Content, Part, Blob
        content = Content(parts=[
            Part(text="What is this document about?"),
            Part(inline_data=Blob(mime_type="application/pdf", data=pdf_bytes))
        ])
        response = client.generate_content(content)
    """
    
    _instance: Optional["GeminiClient"] = None
    
    def __init__(self, model: str = DEFAULT_MODEL):
        from google import genai
        
        self.model = model
        # Pass API key explicitly to avoid "Both GOOGLE_API_KEY and GEMINI_API_KEY are set" warning
        self._client = genai.Client(api_key=_get_api_key())
        logger.debug(f"GeminiClient initialized with model: {model}")
    
    @classmethod
    def get_instance(cls, model: str = DEFAULT_MODEL) -> "GeminiClient":
        """Get singleton instance of GeminiClient."""
        if cls._instance is None:
            cls._instance = cls(model=model)
        return cls._instance
    
    def generate(
        self,
        prompt: Union[str, Any],
        model: Optional[str] = None,
    ) -> str:
        """
        Generate content synchronously.
        
        Args:
            prompt: Text prompt or Content object
            model: Optional model override
            
        Returns:
            Generated text response
        """
        try:
            response = self._client.models.generate_content(
                model=model or self.model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise
    
    async def generate_async(
        self,
        prompt: Union[str, Any],
        model: Optional[str] = None,
    ) -> str:
        """
        Generate content asynchronously.
        
        Args:
            prompt: Text prompt or Content object
            model: Optional model override
            
        Returns:
            Generated text response
        """
        try:
            response = await self._client.aio.models.generate_content(
                model=model or self.model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini async generation error: {e}")
            raise
    
    def generate_content(
        self,
        contents: Any,
        model: Optional[str] = None,
        config: Optional[Any] = None,
    ) -> Any:
        """
        Generate content with full control over request parameters.
        
        Args:
            contents: Content object or list of content
            model: Optional model override
            config: Optional GenerateContentConfig
            
        Returns:
            Full response object
        """
        kwargs = {
            "model": model or self.model,
            "contents": contents,
        }
        if config:
            kwargs["config"] = config
        
        return self._client.models.generate_content(**kwargs)
    
    async def generate_content_async(
        self,
        contents: Any,
        model: Optional[str] = None,
        config: Optional[Any] = None,
    ) -> Any:
        """
        Generate content asynchronously with full control.
        
        Args:
            contents: Content object or list of content
            model: Optional model override
            config: Optional GenerateContentConfig
            
        Returns:
            Full response object
        """
        kwargs = {
            "model": model or self.model,
            "contents": contents,
        }
        if config:
            kwargs["config"] = config
        
        return await self._client.aio.models.generate_content(**kwargs)


# =============================================================================
# GeminiLangChain - LangChain Wrapper
# =============================================================================

class GeminiLangChain:
    """
    LangChain-based Gemini wrapper for agent workflows.
    
    Use this for:
    - LangGraph agent workflows
    - Chain-based processing
    - Tool integration
    - SQL query generation
    
    Examples:
        # General purpose LLM
        llm = GeminiLangChain.get_llm()
        response = llm.invoke([HumanMessage(content="Hello")])
        
        # SQL generation LLM (with safety disabled)
        sql_llm = GeminiLangChain.get_sql_llm()
    """
    
    _llm_instance = None
    _sql_llm_instance = None
    
    @classmethod
    def get_llm(
        cls,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_output_tokens: int = DEFAULT_MAX_TOKENS,
        convert_system_message_to_human: bool = True,
    ):
        """
        Get a general-purpose LangChain Gemini LLM.
        
        Args:
            model: Model name
            temperature: Response temperature (0.0 = deterministic)
            max_output_tokens: Maximum tokens in response
            convert_system_message_to_human: Convert system messages for Gemini compatibility
            
        Returns:
            ChatGoogleGenerativeAI instance
        """
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        if cls._llm_instance is None:
            cls._llm_instance = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=_get_api_key(),
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                convert_system_message_to_human=convert_system_message_to_human,
            )
            logger.debug(f"LangChain LLM initialized with model: {model}")
        
        return cls._llm_instance
    
    @classmethod
    def get_sql_llm(
        cls,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.0,
        max_output_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Get a LangChain Gemini LLM optimized for SQL generation.
        
        This LLM has:
        - Safety settings disabled (for technical content)
        - Temperature set to 0 (deterministic output)
        - System message conversion enabled
        
        Returns:
            ChatGoogleGenerativeAI instance configured for SQL
        """
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        if cls._sql_llm_instance is None:
            cls._sql_llm_instance = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=_get_api_key(),
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                convert_system_message_to_human=True,
                safety_settings=SAFETY_SETTINGS_DISABLED,
            )
            logger.debug(f"SQL LangChain LLM initialized with model: {model}")
        
        return cls._sql_llm_instance
    
    @classmethod
    def create_llm(
        cls,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_output_tokens: int = DEFAULT_MAX_TOKENS,
        safety_settings: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        """
        Create a new LangChain Gemini LLM instance (non-singleton).
        
        Use this when you need a custom configuration that differs
        from the shared instances.
        
        Args:
            model: Model name
            temperature: Response temperature
            max_output_tokens: Maximum tokens
            safety_settings: Optional safety settings dict
            **kwargs: Additional ChatGoogleGenerativeAI parameters
            
        Returns:
            New ChatGoogleGenerativeAI instance
        """
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        config = {
            "model": model,
            "google_api_key": _get_api_key(),
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "convert_system_message_to_human": True,
            **kwargs,
        }
        
        if safety_settings:
            config["safety_settings"] = safety_settings
        
        return ChatGoogleGenerativeAI(**config)


# =============================================================================
# Convenience Functions
# =============================================================================

def get_gemini_client(model: str = DEFAULT_MODEL) -> GeminiClient:
    """
    Get the singleton GeminiClient instance.
    
    Use for direct Google GenAI SDK operations.
    """
    return GeminiClient.get_instance(model)


def get_langchain_llm():
    """
    Get the singleton LangChain LLM instance.
    
    Use for LangChain-based workflows.
    """
    return GeminiLangChain.get_llm()


def get_sql_generator_llm():
    """
    Get the singleton SQL-optimized LangChain LLM instance.
    
    Use for SQL query generation with safety settings disabled.
    """
    return GeminiLangChain.get_sql_llm()
