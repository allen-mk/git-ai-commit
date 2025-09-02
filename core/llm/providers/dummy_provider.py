from typing import AsyncIterable, Union
import asyncio

from core.contracts.provider import LLMProvider
from config.models import ModelConfig
from core.registry import provider_registry


@provider_registry.register("dummy")
class DummyProvider(LLMProvider):
    """A dummy provider for testing purposes that adheres to the async contract."""

    def __init__(self, config: ModelConfig, response: str = "test response"):
        self.config = config
        self._response = response

    async def generate(self, prompt: str, *, stream: bool = False) -> Union[str, AsyncIterable[str]]:
        """Returns a dummy response, either as a string or an async iterable."""
        if stream:
            async def stream_generator():
                for word in self._response.split():
                    yield word
                    await asyncio.sleep(0.05) # Simulate network delay
            return stream_generator()

        await asyncio.sleep(0.1) # Simulate network delay
        return self._response
