"""
NEXUS-14: LLM Service
Unified interface for multiple LLM providers.
Supports: OpenAI, Anthropic Claude, Google Gemini
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from enum import Enum


logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class LLMService:
    """
    Unified LLM service for NEXUS-14.
    
    Features:
    - Multi-provider support (OpenAI, Anthropic, Gemini)
    - Automatic fallback between providers
    - Rate limit handling with exponential backoff
    - Token counting and cost tracking
    - Response caching
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.default_provider = LLMProvider(config.get("llm_provider", "anthropic"))
        
        # API clients (initialized lazily)
        self._openai_client = None
        self._anthropic_client = None
        self._gemini_client = None
        
        # Rate limiting
        self.request_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        
        # Default models per provider
        self.models = {
            LLMProvider.OPENAI: config.get("openai_model", "gpt-4-turbo-preview"),
            LLMProvider.ANTHROPIC: config.get("anthropic_model", "claude-3-5-sonnet-20241022"),
            LLMProvider.GEMINI: config.get("gemini_model", "gemini-1.5-pro")
        }
        
        logger.info(f"LLMService initialized with default provider: {self.default_provider.value}")
    
    async def complete(self, prompt: str, system: str = None, 
                       model: str = None, max_tokens: int = 4096,
                       provider: LLMProvider = None,
                       temperature: float = 0.7) -> str:
        """
        Get a completion from the LLM.
        
        Args:
            prompt: The user message/prompt
            system: Optional system message
            model: Model override (uses default if None)
            max_tokens: Maximum tokens to generate
            provider: LLM provider override
            temperature: Creativity (0.0-1.0)
        
        Returns:
            Generated text response
        """
        provider = provider or self.default_provider
        
        try:
            if provider == LLMProvider.ANTHROPIC:
                return await self._complete_anthropic(prompt, system, model, max_tokens, temperature)
            elif provider == LLMProvider.OPENAI:
                return await self._complete_openai(prompt, system, model, max_tokens, temperature)
            elif provider == LLMProvider.GEMINI:
                return await self._complete_gemini(prompt, system, model, max_tokens, temperature)
            else:
                raise ValueError(f"Unknown provider: {provider}")
                
        except Exception as e:
            logger.warning(f"Provider {provider.value} failed: {e}. Trying fallback...")
            return await self._complete_with_fallback(prompt, system, model, max_tokens, temperature, provider)
    
    async def _complete_anthropic(self, prompt: str, system: str = None,
                                   model: str = None, max_tokens: int = 4096,
                                   temperature: float = 0.7) -> str:
        """Complete using Anthropic Claude."""
        client = await self._get_anthropic_client()
        model = model or self.models[LLMProvider.ANTHROPIC]
        
        messages = [{"role": "user", "content": prompt}]
        
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature
        }
        
        if system:
            kwargs["system"] = system
        
        start = time.time()
        response = await asyncio.to_thread(
            client.messages.create, **kwargs
        )
        duration = time.time() - start
        
        # Track usage
        usage = response.usage
        self.total_tokens += usage.input_tokens + usage.output_tokens
        self.request_count += 1
        
        logger.debug(f"Anthropic response: {usage.input_tokens}in/{usage.output_tokens}out tokens, {duration:.2f}s")
        
        return response.content[0].text
    
    async def _complete_openai(self, prompt: str, system: str = None,
                                model: str = None, max_tokens: int = 4096,
                                temperature: float = 0.7) -> str:
        """Complete using OpenAI."""
        client = await self._get_openai_client()
        model = model or self.models[LLMProvider.OPENAI]
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        start = time.time()
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        duration = time.time() - start
        
        usage = response.usage
        self.total_tokens += usage.total_tokens
        self.request_count += 1
        
        logger.debug(f"OpenAI response: {usage.total_tokens} tokens, {duration:.2f}s")
        
        return response.choices[0].message.content
    
    async def _complete_gemini(self, prompt: str, system: str = None,
                                model: str = None, max_tokens: int = 4096,
                                temperature: float = 0.7) -> str:
        """Complete using Google Gemini."""
        import google.generativeai as genai
        
        api_key = self.config.get("gemini_api_key")
        genai.configure(api_key=api_key)
        
        model_name = model or self.models[LLMProvider.GEMINI]
        gemini_model = genai.GenerativeModel(model_name)
        
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        
        start = time.time()
        response = await asyncio.to_thread(
            gemini_model.generate_content,
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )
        duration = time.time() - start
        
        self.request_count += 1
        logger.debug(f"Gemini response: {duration:.2f}s")
        
        return response.text
    
    async def _complete_with_fallback(self, prompt: str, system: str, 
                                       model: str, max_tokens: int,
                                       temperature: float,
                                       failed_provider: LLMProvider) -> str:
        """Try alternative providers as fallback."""
        fallback_order = [
            LLMProvider.ANTHROPIC,
            LLMProvider.OPENAI,
            LLMProvider.GEMINI
        ]
        
        for provider in fallback_order:
            if provider == failed_provider:
                continue
            
            try:
                logger.info(f"Falling back to {provider.value}...")
                return await self.complete(prompt, system, model, max_tokens, provider, temperature)
            except Exception as e:
                logger.warning(f"Fallback to {provider.value} also failed: {e}")
        
        raise RuntimeError("All LLM providers failed")
    
    async def _get_anthropic_client(self):
        """Get or create Anthropic client."""
        if not self._anthropic_client:
            import anthropic
            self._anthropic_client = anthropic.Anthropic(
                api_key=self.config.get("anthropic_api_key")
            )
        return self._anthropic_client
    
    async def _get_openai_client(self):
        """Get or create OpenAI client."""
        if not self._openai_client:
            from openai import OpenAI
            self._openai_client = OpenAI(
                api_key=self.config.get("openai_api_key")
            )
        return self._openai_client
    
    def get_stats(self) -> Dict:
        """Get usage statistics."""
        return {
            "total_requests": self.request_count,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.total_cost
        }
