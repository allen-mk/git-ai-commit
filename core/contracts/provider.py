from typing import Iterable, Union, Protocol, AsyncIterable

class LLMProvider(Protocol):
    def generate(self, prompt: str, *, stream: bool = False) -> Union[str, Iterable[str]]:
        ...

    async def agenerate(self, prompt: str, *, stream: bool = False) -> Union[str, AsyncIterable[str]]:
        ...
