from typing import Iterable, Union

from core.contracts.provider import LLMProvider
from core.registry import provider_registry


@provider_registry.register("dummy")
class DummyProvider(LLMProvider):
    """A dummy provider for testing purposes."""

    def __init__(self, response: str = "test response"):
        self._response = response

    def generate(self, prompt: str, *, stream: bool = False) -> Union[str, Iterable[str]]:
        """Returns a dummy response."""
        if stream:
            return iter(self._response.split())
        return self._response
