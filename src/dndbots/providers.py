"""Model provider abstraction for multi-provider support.

Supports OpenAI, OpenRouter, and future providers (Claude, DeepSeek, Grok).
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

from autogen_core.models import ModelFamily, ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient


# Default model info for unknown models (assume modern LLM capabilities)
DEFAULT_MODEL_INFO = ModelInfo(
    vision=False,
    function_calling=True,
    json_output=True,
    family=ModelFamily.UNKNOWN,
    structured_output=True,
)


class Provider(Enum):
    """Supported model providers."""

    OPENAI = "openai"
    OPENROUTER = "openrouter"
    # Future providers:
    # ANTHROPIC = "anthropic"
    # DEEPSEEK = "deepseek"
    # GROK = "grok"


@dataclass
class ProviderConfig:
    """Configuration for a model provider."""

    base_url: str | None
    api_key_env: str
    default_model: str
    model_aliases: dict[str, str]  # Maps friendly names to provider model IDs


# Provider configurations
PROVIDER_CONFIGS: dict[Provider, ProviderConfig] = {
    Provider.OPENAI: ProviderConfig(
        base_url=None,  # Use default
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o",
        model_aliases={
            "gpt-4o": "gpt-4o",
            "gpt-4o-mini": "gpt-4o-mini",
            "gpt-4-turbo": "gpt-4-turbo",
            "gpt-4": "gpt-4",
            "gpt-3.5-turbo": "gpt-3.5-turbo",
        },
    ),
    Provider.OPENROUTER: ProviderConfig(
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        default_model="openai/gpt-4o",
        model_aliases={
            # OpenAI models via OpenRouter
            "gpt-4o": "openai/gpt-4o",
            "gpt-4o-mini": "openai/gpt-4o-mini",
            "gpt-4-turbo": "openai/gpt-4-turbo",
            # Anthropic models via OpenRouter
            "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
            "claude-3-opus": "anthropic/claude-3-opus",
            "claude-3-sonnet": "anthropic/claude-3-sonnet",
            "claude-3-haiku": "anthropic/claude-3-haiku",
            # Google models via OpenRouter
            "gemini-pro": "google/gemini-pro-1.5",
            "gemini-flash": "google/gemini-flash-1.5",
            # Meta models via OpenRouter
            "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",
            "llama-3.1-8b": "meta-llama/llama-3.1-8b-instruct",
            # DeepSeek via OpenRouter
            "deepseek-chat": "deepseek/deepseek-chat",
            "deepseek-coder": "deepseek/deepseek-coder",
            # Mistral via OpenRouter
            "mistral-large": "mistralai/mistral-large",
            "mixtral-8x7b": "mistralai/mixtral-8x7b-instruct",
        },
    ),
}


def get_provider_from_env() -> Provider:
    """Detect provider from environment variables.

    Checks for API keys in order of preference.

    Returns:
        Detected provider based on available API keys
    """
    # Check OpenRouter first (user explicitly chose it)
    if os.getenv("OPENROUTER_API_KEY"):
        return Provider.OPENROUTER

    # Fall back to OpenAI
    if os.getenv("OPENAI_API_KEY"):
        return Provider.OPENAI

    # Default to OpenAI (will fail later if no key)
    return Provider.OPENAI


def resolve_model(provider: Provider, model: str) -> str:
    """Resolve a model name to provider-specific model ID.

    Args:
        provider: The provider to use
        model: Model name (can be alias or full ID)

    Returns:
        Provider-specific model ID
    """
    config = PROVIDER_CONFIGS[provider]

    # Check if it's an alias
    if model in config.model_aliases:
        return config.model_aliases[model]

    # Assume it's already a full model ID
    return model


def create_model_client(
    provider: Provider | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> OpenAIChatCompletionClient:
    """Create a model client for the specified provider.

    Args:
        provider: Provider to use (auto-detected from env if None)
        model: Model name or alias (uses provider default if None)
        **kwargs: Additional arguments passed to the client

    Returns:
        Configured model client

    Raises:
        ValueError: If required API key is not set
    """
    # Auto-detect provider if not specified
    if provider is None:
        provider = get_provider_from_env()

    config = PROVIDER_CONFIGS[provider]

    # Get API key
    api_key = os.getenv(config.api_key_env)
    if not api_key:
        raise ValueError(
            f"{config.api_key_env} not set. "
            f"Please set it in your environment or .env file."
        )

    # Resolve model name
    if model is None:
        model = config.default_model
    else:
        model = resolve_model(provider, model)

    # Build client kwargs
    client_kwargs: dict[str, Any] = {
        "model": model,
        "api_key": api_key,
        **kwargs,
    }

    # Add base_url if provider requires it
    if config.base_url:
        client_kwargs["base_url"] = config.base_url

    # For non-OpenAI providers, we need to provide model_info
    # since AutoGen doesn't know about OpenRouter model names
    if provider != Provider.OPENAI and "model_info" not in client_kwargs:
        client_kwargs["model_info"] = DEFAULT_MODEL_INFO

    return OpenAIChatCompletionClient(**client_kwargs)


def list_available_models(provider: Provider) -> list[str]:
    """List available model aliases for a provider.

    Args:
        provider: The provider to list models for

    Returns:
        List of model alias names
    """
    config = PROVIDER_CONFIGS[provider]
    return list(config.model_aliases.keys())
