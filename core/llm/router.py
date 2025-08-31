from config.models import ModelConfig
from core.contracts.provider import LLMProvider
from core.registry import provider_registry
from utils.errors import ProviderError

def get_provider(config: ModelConfig) -> LLMProvider:
    """
    Factory function to get an LLM provider instance based on the config.

    Args:
        config: The model configuration.

    Returns:
        An instance of a class that implements the LLMProvider protocol.

    Raises:
        ProviderError: If the provider is not found or fails to be created.
    """
    try:
        # The provider's __init__ is expected to take the config object.
        provider_instance = provider_registry.create(config.provider, config=config)
        return provider_instance
    except KeyError:
        available = list(provider_registry.keys())
        raise ProviderError(
            f"Unknown provider '{config.provider}'. "
            f"Available providers: {available}"
        )
    except Exception as e:
        # Catch other potential instantiation errors from the provider's __init__
        raise ProviderError(f"Failed to create provider '{config.provider}': {e}") from e
