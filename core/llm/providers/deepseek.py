import os
import httpx
import json
from typing import Iterable, Union, Generator

from core.contracts.provider import LLMProvider
from config.models import ModelConfig
from core.registry import provider_registry
from utils.errors import ProviderError

@provider_registry.register("deepseek")
class DeepSeekProvider(LLMProvider):
    """
    一个用于 DeepSeek API 的 Provider。
    该 API 与 OpenAI API 兼容。
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        # API 密钥管理
        self._api_key = config.api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self._api_key:
            raise ProviderError("DeepSeek API key not found. Please set it in the config or as an environment variable DEEPSEEK_API_KEY.")

        # 初始化 httpx 客户端
        self._client = httpx.Client(
            base_url="https://api.deepseek.com/v1", # 使用 v1 端点以保持兼容性
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.config.timeout_sec,
        )

    def _request(self, payload: dict) -> httpx.Response:
        """
        发送 HTTP 请求。
        """
        try:
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise ProviderError(f"Request to DeepSeek timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            try:
                error_details = e.response.json()
                error_message = error_details.get("error", {}).get("message", e.response.text)
            except json.JSONDecodeError:
                error_message = e.response.text
            raise ProviderError(f"DeepSeek API error ({e.response.status_code}): {error_message}") from e
        except httpx.RequestError as e:
            raise ProviderError(f"An unexpected network error occurred: {e}") from e

    def _build_payload(self, prompt: str, stream: bool) -> dict:
        """
        构建请求体。
        """
        return {
            "model": self.config.name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
        }

    def _process_stream_response(self, response: httpx.Response) -> Generator[str, None, None]:
        """
        处理流式响应。
        """
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
                        continue
        finally:
            response.close()

    def generate(self, prompt: str, *, stream: bool = False) -> Union[str, Iterable[str]]:
        """
        从 DeepSeek LLM 生成响应。
        """
        payload = self._build_payload(prompt, stream)

        if stream:
            response = self._client.stream("POST", "/chat/completions", json=payload)
            return self._process_stream_response(response)
        else:
            response = self._request(payload)
            data = response.json()
            return data["choices"][0]["message"]["content"]
