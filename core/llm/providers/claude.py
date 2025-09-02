import os
import httpx
import json
from typing import AsyncIterable, Union, AsyncGenerator

from core.contracts.provider import LLMProvider
from config.models import ModelConfig
from core.registry import provider_registry
from utils.errors import ProviderError

@provider_registry.register("claude")
class ClaudeProvider(LLMProvider):
    """
    A provider for the Anthropic Claude API, updated for asynchronous operations.
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self._api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ProviderError("Anthropic API key not found. Please set it in the config or as an environment variable ANTHROPIC_API_KEY.")

        self._client = httpx.AsyncClient(
            base_url="https://api.anthropic.com/v1",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=self.config.timeout_sec,
        )

    async def _request(self, payload: dict) -> httpx.Response:
        """
        Sends an HTTP request to the Claude API.
        """
        try:
            response = await self._client.post("/messages", json=payload)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise ProviderError(f"Request to Anthropic timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            try:
                error_details = e.response.json()
                error_message = error_details.get("error", {}).get("message", e.response.text)
            except json.JSONDecodeError:
                error_message = e.response.text
            raise ProviderError(f"Anthropic API error ({e.response.status_code}): {error_message}") from e
        except httpx.RequestError as e:
            raise ProviderError(f"An unexpected network error occurred: {e}") from e

    def _build_payload(self, prompt: str, stream: bool) -> dict:
        """
        Builds the request payload for the API.
        """
        payload = {
            "model": self.config.name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,  # Anthropic requires max_tokens
            "stream": stream,
        }
        # Merge additional parameters, ensuring 'max_tokens' is not overwritten if present
        payload.update(self.config.parameters)
        return payload

    async def _process_stream(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """
        Processes a streaming response from the Claude API.
        """
        try:
            async for line in response.aiter_lines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                if not data_str:
                    continue
                try:
                    chunk = json.loads(data_str)
                    chunk_type = chunk.get("type")
                    if chunk_type == "content_block_delta":
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta":
                            content = delta.get("text")
                            if content:
                                yield content
                    elif chunk_type == "message_stop":
                        break
                except (json.JSONDecodeError, IndexError):
                    continue
        finally:
            await response.aclose()

    async def generate(self, prompt: str, *, stream: bool = False) -> Union[str, AsyncIterable[str]]:
        """
        Generates a response from the Claude LLM, supporting both streaming and non-streaming.
        """
        payload = self._build_payload(prompt, stream)

        if stream:
            async def stream_generator():
                try:
                    async with self._client.stream("POST", "/messages", json=payload) as response:
                        response.raise_for_status()
                        async for chunk in self._process_stream(response):
                            yield chunk
                except httpx.HTTPStatusError as e:
                    error_body = await e.response.aread()
                    try:
                        error_details = json.loads(error_body)
                        error_message = error_details.get("error", {}).get("message", error_body.decode())
                    except json.JSONDecodeError:
                        error_message = error_body.decode()
                    raise ProviderError(f"Anthropic API error ({e.response.status_code}): {error_message}") from e
            return stream_generator()
        else:
            response = await self._request(payload)
            data = response.json()
            return data.get("content", [{}])[0].get("text", "")
