from typing import Any, Mapping

from core.contracts.collector import Collector
from core.registry import collector_registry


@collector_registry.register("dummy")
class DummyCollector(Collector):
    """A dummy collector for testing purposes."""

    def __init__(self, value: int = 42):
        self._value = value

    def collect(self) -> Mapping[str, Any]:
        """Returns a dummy dictionary."""
        return {"dummy_data": "hello", "value": self._value}
