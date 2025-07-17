"""OpenAI model configuration and pricing."""

from typing import Any, Dict

# OpenAI model pricing as of 2024
# Prices are per 1M tokens
OPENAI_MODELS: Dict[str, Dict[str, Any]] = {
    # GPT-4.1 Series
    "gpt-4.1": {
        "name": "GPT-4.1",
        "description": "Latest GPT-4.1 model",
        "input_cost": 2.00,
        "cached_cost": 0.50,
        "output_cost": 8.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "gpt-4.1",
        "supports_caching": True,
    },
    "gpt-4.1-mini": {
        "name": "GPT-4.1 Mini",
        "description": "Smaller GPT-4.1 variant",
        "input_cost": 0.40,
        "cached_cost": 0.10,
        "output_cost": 1.60,
        "context_window": 128000,
        "max_output": 16384,
        "category": "gpt-4.1",
        "supports_caching": True,
    },
    "gpt-4.1-nano": {
        "name": "GPT-4.1 Nano",
        "description": "Smallest GPT-4.1 variant",
        "input_cost": 0.10,
        "cached_cost": 0.025,
        "output_cost": 0.40,
        "context_window": 128000,
        "max_output": 16384,
        "category": "gpt-4.1",
        "supports_caching": True,
    },
    # GPT-4.5 Series
    "gpt-4.5-preview": {
        "name": "GPT-4.5 Preview",
        "description": "Preview of next generation model",
        "input_cost": 75.00,
        "cached_cost": 37.50,
        "output_cost": 150.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "preview",
        "supports_caching": True,
    },
    # GPT-4o Series
    "gpt-4o": {
        "name": "GPT-4o",
        "description": "Optimized GPT-4 model",
        "input_cost": 2.50,
        "cached_cost": 1.25,
        "output_cost": 10.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "gpt-4o",
        "supports_caching": True,
    },
    "gpt-4o-audio-preview": {
        "name": "GPT-4o Audio Preview",
        "description": "GPT-4o with audio capabilities",
        "input_cost": 2.50,
        "cached_cost": None,
        "output_cost": 10.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "gpt-4o",
        "supports_caching": False,
    },
    "gpt-4o-realtime-preview": {
        "name": "GPT-4o Realtime Preview",
        "description": "GPT-4o for realtime applications",
        "input_cost": 5.00,
        "cached_cost": 2.50,
        "output_cost": 20.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "gpt-4o",
        "supports_caching": True,
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "description": "Affordable small model for simple tasks",
        "input_cost": 0.15,
        "cached_cost": 0.075,
        "output_cost": 0.60,
        "context_window": 128000,
        "max_output": 16384,
        "category": "gpt-4o",
        "supports_caching": True,
    },
    "gpt-4o-mini-audio-preview": {
        "name": "GPT-4o Mini Audio Preview",
        "description": "GPT-4o Mini with audio capabilities",
        "input_cost": 0.15,
        "cached_cost": None,
        "output_cost": 0.60,
        "context_window": 128000,
        "max_output": 16384,
        "category": "gpt-4o",
        "supports_caching": False,
    },
    "gpt-4o-mini-realtime-preview": {
        "name": "GPT-4o Mini Realtime Preview",
        "description": "GPT-4o Mini for realtime applications",
        "input_cost": 0.60,
        "cached_cost": 0.30,
        "output_cost": 2.40,
        "context_window": 128000,
        "max_output": 16384,
        "category": "gpt-4o",
        "supports_caching": True,
    },
    # O1 Series (Reasoning Models)
    "o1": {
        "name": "O1",
        "description": "Advanced reasoning model",
        "input_cost": 15.00,
        "cached_cost": 7.50,
        "output_cost": 60.00,
        "context_window": 128000,
        "max_output": 32768,
        "category": "reasoning",
        "supports_caching": True,
    },
    "o1-pro": {
        "name": "O1 Pro",
        "description": "Professional reasoning model",
        "input_cost": 150.00,
        "cached_cost": None,
        "output_cost": 600.00,
        "context_window": 128000,
        "max_output": 32768,
        "category": "reasoning",
        "supports_caching": False,
    },
    "o1-mini": {
        "name": "O1 Mini",
        "description": "Smaller reasoning model",
        "input_cost": 1.10,
        "cached_cost": 0.55,
        "output_cost": 4.40,
        "context_window": 128000,
        "max_output": 65536,
        "category": "reasoning",
        "supports_caching": True,
    },
    # O3 Series
    "o3": {
        "name": "O3",
        "description": "Next generation model",
        "input_cost": 2.00,
        "cached_cost": 0.50,
        "output_cost": 8.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "next-gen",
        "supports_caching": True,
    },
    "o3-pro": {
        "name": "O3 Pro",
        "description": "Professional next-gen model",
        "input_cost": 20.00,
        "cached_cost": None,
        "output_cost": 80.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "next-gen",
        "supports_caching": False,
    },
    "o3-deep-research": {
        "name": "O3 Deep Research",
        "description": "O3 optimized for research tasks",
        "input_cost": 10.00,
        "cached_cost": 2.50,
        "output_cost": 40.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "next-gen",
        "supports_caching": True,
    },
    "o3-mini": {
        "name": "O3 Mini",
        "description": "Smaller O3 variant",
        "input_cost": 1.10,
        "cached_cost": 0.55,
        "output_cost": 4.40,
        "context_window": 128000,
        "max_output": 16384,
        "category": "next-gen",
        "supports_caching": True,
    },
    # O4 Series
    "o4-mini": {
        "name": "O4 Mini",
        "description": "Latest mini model",
        "input_cost": 1.10,
        "cached_cost": 0.275,
        "output_cost": 4.40,
        "context_window": 128000,
        "max_output": 16384,
        "category": "next-gen",
        "supports_caching": True,
    },
    "o4-mini-deep-research": {
        "name": "O4 Mini Deep Research",
        "description": "O4 Mini for research tasks",
        "input_cost": 2.00,
        "cached_cost": 0.50,
        "output_cost": 8.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "next-gen",
        "supports_caching": True,
    },
    # Specialized Models
    "codex-mini-latest": {
        "name": "Codex Mini Latest",
        "description": "Code generation model",
        "input_cost": 1.50,
        "cached_cost": 0.375,
        "output_cost": 6.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "specialized",
        "supports_caching": True,
    },
    "gpt-4o-mini-search-preview": {
        "name": "GPT-4o Mini Search Preview",
        "description": "GPT-4o Mini with search capabilities",
        "input_cost": 0.15,
        "cached_cost": None,
        "output_cost": 0.60,
        "context_window": 128000,
        "max_output": 16384,
        "category": "specialized",
        "supports_caching": False,
    },
    "gpt-4o-search-preview": {
        "name": "GPT-4o Search Preview",
        "description": "GPT-4o with search capabilities",
        "input_cost": 2.50,
        "cached_cost": None,
        "output_cost": 10.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "specialized",
        "supports_caching": False,
    },
    "computer-use-preview": {
        "name": "Computer Use Preview",
        "description": "Model for computer interaction",
        "input_cost": 3.00,
        "cached_cost": None,
        "output_cost": 12.00,
        "context_window": 128000,
        "max_output": 16384,
        "category": "specialized",
        "supports_caching": False,
    },
    # Legacy Models
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo",
        "description": "Fast, inexpensive model for simple tasks",
        "input_cost": 0.50,
        "cached_cost": None,
        "output_cost": 1.50,
        "context_window": 16385,
        "max_output": 4096,
        "category": "legacy",
        "supports_caching": False,
    },
}

# Default model for new plans
DEFAULT_MODEL = "gpt-4o-mini"

# Model categories for UI grouping
MODEL_CATEGORIES = {
    "gpt-4.1": "GPT-4.1 Series",
    "gpt-4o": "GPT-4o Series",
    "reasoning": "Reasoning Models (O1)",
    "next-gen": "Next Generation Models",
    "specialized": "Specialized Models",
    "preview": "Preview Models",
    "legacy": "Legacy Models",
}

# Models recommended for different use cases
RECOMMENDED_MODELS = {
    "best_quality": ["o1-pro", "gpt-4.5-preview", "o1"],
    "best_value": ["gpt-4o-mini", "gpt-4.1-mini", "gpt-3.5-turbo"],
    "balanced": ["gpt-4o", "gpt-4.1", "o3"],
    "research": ["o3-deep-research", "o4-mini-deep-research", "o1"],
    "realtime": ["gpt-4o-realtime-preview", "gpt-4o-mini-realtime-preview"],
    "budget": ["gpt-4.1-nano", "gpt-3.5-turbo", "gpt-4o-mini"],
}


def get_model_config(model_id: str) -> Dict[str, Any]:
    """Get configuration for a specific model."""
    return OPENAI_MODELS.get(model_id, OPENAI_MODELS[DEFAULT_MODEL])


def calculate_cost(
    model_id: str, prompt_tokens: int, completion_tokens: int, cached_tokens: int = 0
) -> Dict[str, float]:
    """Calculate cost for API usage with support for cached tokens.

    Args:
        model_id: The model identifier
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        cached_tokens: Number of cached tokens (if applicable)

    Returns:
        Dictionary with cost breakdown
    """
    model_config = get_model_config(model_id)

    # Calculate input cost (cached vs non-cached)
    if cached_tokens > 0 and model_config.get("cached_cost") is not None:
        non_cached_tokens = max(0, prompt_tokens - cached_tokens)
        input_cost = (non_cached_tokens / 1_000_000) * model_config["input_cost"] + (
            cached_tokens / 1_000_000
        ) * model_config["cached_cost"]
    else:
        input_cost = (prompt_tokens / 1_000_000) * model_config["input_cost"]

    # Calculate output cost
    output_cost = (completion_tokens / 1_000_000) * model_config["output_cost"]

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": input_cost + output_cost,
        "cached_tokens": cached_tokens,
        "supports_caching": model_config.get("supports_caching", False),
    }


def get_models_by_category(category: str) -> Dict[str, Dict[str, Any]]:
    """Get all models in a specific category."""
    return {
        model_id: config
        for model_id, config in OPENAI_MODELS.items()
        if config.get("category") == category
    }


def get_recommended_models(use_case: str) -> list[Dict[str, Any]]:
    """Get recommended models for a specific use case."""
    model_ids = RECOMMENDED_MODELS.get(use_case, [])
    return [
        {"id": model_id, **OPENAI_MODELS[model_id]}
        for model_id in model_ids
        if model_id in OPENAI_MODELS
    ]
