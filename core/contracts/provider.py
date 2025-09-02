from typing import AsyncIterable, Protocol, Union


class LLMProvider(Protocol):
    """A protocol for LLM providers."""

    async def generate(
        self, prompt: str, *, stream: bool = False
    ) -> Union[str, AsyncIterable[str]]:
        """
        Generates a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM.
            stream: Whether to stream the response.

        Returns:
            The LLM's response, either as a string or an async iterable of strings.
        """
        ...
