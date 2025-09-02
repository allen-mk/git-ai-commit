import os
import httpx
import json
from typing import AsyncIterable, Union, AsyncGenerator

from core.contracts.provider import LLMProvider
from config.models import ModelConfig
from core.registry import provider_registry
from utils.errors import ProviderError


@provider_registry.register("openai")
class OpenAIProvider(LLMProvider):
    """
    A provider for OpenAI's API, updated for asynchronous operations.
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self._api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ProviderError("OpenAI API key not found. Please set it in the config or as an environment variable OPENAI_API_KEY.")

        self._client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.config.timeout_sec,
        )

    async def _request(self, payload: dict) -> httpx.Response:
        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise ProviderError(f"Request to OpenAI timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            try:
                error_details = e.response.json()
                error_message = error_details.get("error", {}).get("message", e.response.text)
            except json.JSONDecodeError:
                error_message = e.response.text
            raise ProviderError(f"OpenAI API error ({e.response.status_code}): {error_message}") from e
        except httpx.RequestError as e:
            raise ProviderError(f"An unexpected network error occurred: {e}") from e

    def _build_payload(self, prompt: str, stream: bool) -> dict:
        return {
            "model": self.config.name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            **self.config.parameters,
        }

    async def _process_stream(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """Processes a streaming response from the OpenAI API."""
        try:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    chunk_str = line[len("data:"):].strip()
                    if chunk_str == "[DONE]":
                        break
                    if not chunk_str:
                        continue
                    try:
                        chunk = json.loads(chunk_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, IndexError):
                        continue
        finally:
            await response.aclose()

    async def generate(self, prompt: str, *, stream: bool = False) -> Union[str, AsyncIterable[str]]:
        """
        Generates a response from the OpenAI LLM, supporting both streaming and non-streaming.
        """
        payload = self._build_payload(prompt, stream)

        if stream:
            async def stream_generator():
                try:
                    async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                        response.raise_for_status()
                        async for chunk in self._process_stream(response):
                            yield chunk
                except httpx.HTTPStatusError as e:
                    # Handle case where the error happens during stream setup
                    error_body = await e.response.aread()
                    try:
                        error_details = json.loads(error_body)
                        error_message = error_details.get("error", {}).get("message", error_body.decode())
                    except json.JSONDecodeError:
                        error_message = error_body.decode()
                    raise ProviderError(f"OpenAI API error ({e.response.status_code}): {error_message}") from e

            return stream_generator()
        else:
            response = await self._request(payload)
            data = response.json()
            return data["choices"][0]["message"]["content"]
