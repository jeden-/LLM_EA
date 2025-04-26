"""
napisz Module responsible for communication with various Large Language Model providers.

This module:
1. Provides a unified interface for interaction with different LLM providers
2. Handles API communication, retries, and error handling
3. Supports configuration of provider-specific settings
4. Manages rate limiting and token usage
5. Implements caching for efficiency
"""

import json
import logging
import time
import os
import hashlib
import requests
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timedelta
import openai
from openai import OpenAI
from anthropic import Anthropic
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class LLMInterface:
    """
    Interface for interacting with different LLM providers.
    
    Supported providers:
    - OpenAI (GPT-3.5, GPT-4)
    - Anthropic (Claude)
    - Local models through API
    """
    
    def __init__(
        self, 
        default_provider: str = "openai",
        cache_enabled: bool = True,
        cache_dir: str = ".llm_cache",
        max_retries: int = 3,
        timeout: int = 60
    ):
        """
        Initialize the LLM interface.
        
        Args:
            default_provider: Default LLM provider to use
            cache_enabled: Whether to enable response caching
            cache_dir: Directory to store cached responses
            max_retries: Maximum number of retries for failed requests
            timeout: Request timeout in seconds
        """
        self.default_provider = default_provider
        self.cache_enabled = cache_enabled
        self.cache_dir = cache_dir
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Credentials and API keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.local_api_url = os.getenv("LOCAL_LLM_API_URL")
        
        # Initialize clients
        self._init_clients()
        
        # Cache setup
        if self.cache_enabled:
            os.makedirs(self.cache_dir, exist_ok=True)
        
        # Provider configurations
        self.provider_configs = {
            "openai": {
                "default_model": "gpt-4o",
                "temperature": 0.2,
                "max_tokens": 4000,
                "top_p": 1.0,
                "frequency_penalty": 0,
                "presence_penalty": 0,
            },
            "anthropic": {
                "default_model": "claude-3-opus-20240229",
                "temperature": 0.2,
                "max_tokens": 4000,
                "top_p": 0.9,
            },
            "local": {
                "default_model": "default",
                "temperature": 0.2,
                "max_tokens": 2000,
                "top_p": 1.0,
            },
        }
        
        # Usage tracking
        self.usage_stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "errors": 0,
            "cache_hits": 0,
            "provider_usage": {},
        }
        
        logger.info(f"LLM Interface initialized with default provider: {default_provider}")
    
    def _init_clients(self):
        """Initialize API clients for each provider."""
        self.clients = {}
        
        # OpenAI client
        if self.openai_api_key:
            try:
                self.clients["openai"] = OpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        else:
            logger.warning("OpenAI API key not found, OpenAI provider will not be available")
        
        # Anthropic client
        if self.anthropic_api_key:
            try:
                self.clients["anthropic"] = Anthropic(api_key=self.anthropic_api_key)
                logger.info("Anthropic client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {str(e)}")
        else:
            logger.warning("Anthropic API key not found, Claude provider will not be available")
    
    def update_provider_config(self, provider: str, config_updates: Dict[str, Any]):
        """
        Update configuration for a specific provider.
        
        Args:
            provider: Provider name to update
            config_updates: Dictionary of configuration updates
        """
        if provider not in self.provider_configs:
            raise ValueError(f"Unknown provider: {provider}")
        
        self.provider_configs[provider].update(config_updates)
        logger.info(f"Updated configuration for provider: {provider}")
    
    def _get_cache_path(self, provider: str, model: str, prompt: str, system_prompt: str) -> str:
        """
        Get the cache file path for a request.
        
        Args:
            provider: LLM provider name
            model: Model name
            prompt: User prompt
            system_prompt: System prompt
            
        Returns:
            Path to the cache file
        """
        # Create a unique hash of the request
        content = f"{provider}|{model}|{prompt}|{system_prompt}"
        hash_value = hashlib.md5(content.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_value}.json")
    
    def _check_cache(self, provider: str, model: str, prompt: str, system_prompt: str) -> Optional[str]:
        """
        Check if a cached response exists for this request.
        
        Args:
            provider: LLM provider name
            model: Model name
            prompt: User prompt
            system_prompt: System prompt
            
        Returns:
            Cached response or None if not found
        """
        if not self.cache_enabled:
            return None
        
        cache_path = self._get_cache_path(provider, model, prompt, system_prompt)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Check if cache is still valid (30 day expiry)
                cache_time = datetime.fromisoformat(cache_data["timestamp"])
                if datetime.now() - cache_time > timedelta(days=30):
                    logger.debug("Cache expired")
                    return None
                
                self.usage_stats["cache_hits"] += 1
                logger.debug(f"Cache hit for {provider}/{model}")
                return cache_data["response"]
            
            except Exception as e:
                logger.warning(f"Error reading cache: {str(e)}")
                return None
        
        return None
    
    def _save_to_cache(self, provider: str, model: str, prompt: str, system_prompt: str, response: str):
        """
        Save a response to the cache.
        
        Args:
            provider: LLM provider name
            model: Model name
            prompt: User prompt
            system_prompt: System prompt
            response: Response to cache
        """
        if not self.cache_enabled:
            return
        
        cache_path = self._get_cache_path(provider, model, prompt, system_prompt)
        
        try:
            cache_data = {
                "provider": provider,
                "model": model,
                "timestamp": datetime.now().isoformat(),
                "response": response
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Response cached for {provider}/{model}")
        
        except Exception as e:
            logger.warning(f"Error saving to cache: {str(e)}")
    
    def _call_openai(self, prompt: str, system_prompt: str, model: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Call OpenAI API.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: Model name
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (response_text, usage_stats)
        """
        if "openai" not in self.clients:
            raise ValueError("OpenAI client not initialized")
        
        client = self.clients["openai"]
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Prepare parameters
        params = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.provider_configs["openai"]["temperature"]),
            "max_tokens": kwargs.get("max_tokens", self.provider_configs["openai"]["max_tokens"]),
            "top_p": kwargs.get("top_p", self.provider_configs["openai"]["top_p"]),
            "frequency_penalty": kwargs.get("frequency_penalty", self.provider_configs["openai"]["frequency_penalty"]),
            "presence_penalty": kwargs.get("presence_penalty", self.provider_configs["openai"]["presence_penalty"]),
        }
        
        # Make the API call
        response = client.chat.completions.create(**params)
        
        # Extract the response text
        response_text = response.choices[0].message.content
        
        # Extract usage statistics
        usage_stats = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        
        return response_text, usage_stats
    
    def _call_anthropic(self, prompt: str, system_prompt: str, model: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Call Anthropic Claude API.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: Model name
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (response_text, usage_stats)
        """
        if "anthropic" not in self.clients:
            raise ValueError("Anthropic client not initialized")
        
        client = self.clients["anthropic"]
        
        # Prepare parameters
        params = {
            "model": model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.provider_configs["anthropic"]["temperature"]),
            "max_tokens": kwargs.get("max_tokens", self.provider_configs["anthropic"]["max_tokens"]),
            "top_p": kwargs.get("top_p", self.provider_configs["anthropic"]["top_p"]),
        }
        
        # Make the API call
        response = client.messages.create(**params)
        
        # Extract the response text
        response_text = response.content[0].text
        
        # Extract usage statistics (anthropic doesn't provide detailed token usage)
        usage_stats = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        
        return response_text, usage_stats
    
    def _call_local_api(self, prompt: str, system_prompt: str, model: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Call a local LLM API.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: Model name (ignored for local API)
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (response_text, usage_stats)
        """
        if not self.local_api_url:
            raise ValueError("Local LLM API URL not configured")
        
        # Prepare the request payload
        payload = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "temperature": kwargs.get("temperature", self.provider_configs["local"]["temperature"]),
            "max_tokens": kwargs.get("max_tokens", self.provider_configs["local"]["max_tokens"]),
            "top_p": kwargs.get("top_p", self.provider_configs["local"]["top_p"]),
        }
        
        # Make the API call
        response = requests.post(
            self.local_api_url,
            json=payload,
            timeout=self.timeout
        )
        
        # Check for errors
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        # Extract the response text and usage stats
        response_text = result.get("response", "")
        usage_stats = result.get("usage", {"total_tokens": 0})
        
        return response_text, usage_stats
    
    def generate_response(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a response from an LLM.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            provider_name: LLM provider to use (default if None)
            model: Model name to use (provider default if None)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated response text
        """
        start_time = time.time()
        provider = provider_name or self.default_provider
        
        # Select provider config
        if provider not in self.provider_configs:
            logger.warning(f"Unknown provider: {provider}, falling back to {self.default_provider}")
            provider = self.default_provider
        
        # Get provider config
        provider_config = self.provider_configs[provider]
        
        # Select model
        if model is None:
            model = provider_config["default_model"]
        
        logger.info(f"Generating response using {provider}/{model}")
        
        # Check cache first
        cached_response = self._check_cache(provider, model, prompt, system_prompt)
        if cached_response:
            logger.info(f"Returning cached response (provider: {provider}, model: {model})")
            return cached_response
        
        # Track usage
        self.usage_stats["total_requests"] += 1
        if provider not in self.usage_stats["provider_usage"]:
            self.usage_stats["provider_usage"][provider] = {"requests": 0, "tokens": 0}
        self.usage_stats["provider_usage"][provider]["requests"] += 1
        
        # Call the appropriate provider with retries
        for attempt in range(self.max_retries):
            try:
                if provider == "openai":
                    response_text, usage_stats = self._call_openai(prompt, system_prompt, model, **kwargs)
                elif provider == "anthropic":
                    response_text, usage_stats = self._call_anthropic(prompt, system_prompt, model, **kwargs)
                elif provider == "local":
                    response_text, usage_stats = self._call_local_api(prompt, system_prompt, model, **kwargs)
                else:
                    raise ValueError(f"Unsupported provider: {provider}")
                
                # Update usage statistics
                if "total_tokens" in usage_stats:
                    self.usage_stats["total_tokens"] += usage_stats["total_tokens"]
                    self.usage_stats["provider_usage"][provider]["tokens"] += usage_stats["total_tokens"]
                
                # Cache the response
                self._save_to_cache(provider, model, prompt, system_prompt, response_text)
                
                # Log success
                execution_time = time.time() - start_time
                logger.info(f"Response generated successfully in {execution_time:.2f}s")
                
                return response_text
            
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{self.max_retries} failed: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        # All retries failed
        self.usage_stats["errors"] += 1
        logger.error(f"Failed to generate response after {self.max_retries} attempts")
        raise Exception(f"Failed to generate response from {provider}/{model} after {self.max_retries} attempts")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get current usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        return self.usage_stats

# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create LLM interface
    llm = LLMInterface()
    
    # Example prompt
    prompt = "Analyze the EUR/USD market situation with the following data:\n- Current price: 1.0821\n- RSI: 58.3\n- MACD: Bullish crossover\n- Recent trend: Upward for 5 days"
    system_prompt = "You are a professional forex market analyst. Provide a concise analysis in JSON format with market direction, key levels, and confidence score."
    
    # Generate response
    try:
        response = llm.generate_response(prompt, system_prompt)
        print("Response:")
        print(response)
        
        # Print usage stats
        print("\nUsage Statistics:")
        print(json.dumps(llm.get_usage_stats(), indent=2))
    
    except Exception as e:
        print(f"Error: {str(e)}") 