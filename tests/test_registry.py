import pytest

# Import the dummy components to ensure they are registered
from core.collectors import dummy_collector
from core.llm.providers import dummy_provider
from core.registry import Registry, collector_registry, provider_registry


def test_registry_get_component():
    """Tests that a component can be retrieved from the registry."""
    collector_class = collector_registry.get("dummy")
    assert collector_class is not None
    assert collector_class.__name__ == "DummyCollector"

    provider_class = provider_registry.get("dummy")
    assert provider_class is not None
    assert provider_class.__name__ == "DummyProvider"


from config.models import ModelConfig


@pytest.mark.asyncio
async def test_registry_create_component():
    """Tests that a component can be instantiated from the registry."""
    collector = collector_registry.create("dummy")
    assert isinstance(collector, dummy_collector.DummyCollector)
    assert collector.collect() == {"dummy_data": "hello", "value": 42}

    collector_with_arg = collector_registry.create("dummy", value=100)
    assert collector_with_arg.collect() == {"dummy_data": "hello", "value": 100}

    dummy_config = ModelConfig()
    provider = provider_registry.create("dummy", config=dummy_config)
    assert isinstance(provider, dummy_provider.DummyProvider)
    assert await provider.generate("test") == "test response"

    provider_with_arg = provider_registry.create(
        "dummy", config=dummy_config, response="custom response"
    )
    assert await provider_with_arg.generate("test") == "custom response"


def test_registry_get_unregistered_component():
    """Tests that getting an unregistered component raises a KeyError."""
    with pytest.raises(KeyError):
        collector_registry.get("nonexistent")

    with pytest.raises(KeyError):
        provider_registry.get("nonexistent")


def test_registry_register_duplicate_component():
    """Tests that registering a component with a duplicate name raises a ValueError."""
    with pytest.raises(ValueError):
        @collector_registry.register("dummy")
        class AnotherDummyCollector:
            pass

    with pytest.raises(ValueError):
        @provider_registry.register("dummy")
        class AnotherDummyProvider:
            pass


def test_registry_contains():
    """Tests the `__contains__` method."""
    assert "dummy" in collector_registry
    assert "nonexistent" not in collector_registry


def test_registry_iter():
    """Tests the `__iter__` method."""
    keys = list(iter(collector_registry))
    assert "dummy" in keys


def test_registry_keys():
    """Tests the `keys` method."""
    keys = collector_registry.keys()
    assert "dummy" in keys
