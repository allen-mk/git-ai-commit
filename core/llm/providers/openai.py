import os
import httpx
import json
from typing import Iterable, Union, Generator

from core.contracts.provider import LLMProvider
from config.models import ModelConfig
from core.registry import provider_registry
from utils.errors import ProviderError


@provider_registry.register("openai")
class OpenAIProvider(LLMProvider):
    """
    A provider for OpenAI's API.
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self._api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ProviderError("OpenAI API key not found. Please set it in the config or as an environment variable OPENAI_API_KEY.")

        self._client = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.config.timeout_sec,
        )

    def _request(self, payload: dict) -> httpx.Response:
        try:
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise ProviderError(f"Request to OpenAI timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            # Try to parse the error response from OpenAI
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
        }

    def _process_stream_response(self, response: httpx.Response) -> Generator[str, None, None]:
        """Processes a streaming response from the OpenAI API."""
        try:
            for line in response.iter_lines():
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
                    except json.JSONDecodeError:
                        # Sometimes a stray line might not be valid JSON, skip it
                        continue
        finally:
            response.close()

    def generate(self, prompt: str, *, stream: bool = False) -> Union[str, Iterable[str]]:
        """
        Generates a response from the OpenAI LLM.
        """
        payload = self._build_payload(prompt, stream)

        if stream:
            response = self._client.stream("POST", "/chat/completions", json=payload)
            return self._process_stream_response(response)
        else:
            response = self._request(payload)
            data = response.json()
            return data["choices"][0]["message"]["content"]
