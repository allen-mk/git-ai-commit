import os
import httpx
import json
from typing import Iterable, Union, Generator

from core.contracts.provider import LLMProvider
from config.models import ModelConfig
from core.registry import provider_registry
from utils.errors import ProviderError

@provider_registry.register("claude")
class ClaudeProvider(LLMProvider):
    """
    一个用于 Anthropic Claude API 的 Provider。
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        # API 密钥管理，优先从配置中读取，否则从环境变量 ANTHROPIC_API_KEY 读取
        self._api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ProviderError("Anthropic API key not found. Please set it in the config or as an environment variable ANTHROPIC_API_KEY.")

        # 初始化 httpx 客户端
        self._client = httpx.Client(
            base_url="https://api.anthropic.com/v1",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=self.config.timeout_sec,
        )

    def _request(self, payload: dict) -> httpx.Response:
        """
        发送 HTTP 请求到 Claude API。
        """
        try:
            response = self._client.post("/messages", json=payload)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise ProviderError(f"Request to Anthropic timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            # 尝试解析来自 Anthropic 的错误响应
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
        构建发送给 API 的请求体。
        """
        return {
            "model": self.config.name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,  # Anthropic requires max_tokens
            "stream": stream,
        }

    def _process_stream_response(self, response: httpx.Response) -> Generator[str, None, None]:
        """
        处理来自 Claude API 的流式响应。
        Anthropic streaming uses Server-Sent Events (SSE).
        """
        try:
            for line in response.iter_lines():
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
                except json.JSONDecodeError:
                    continue
        finally:
            response.close()

    def generate(self, prompt: str, *, stream: bool = False) -> Union[str, Iterable[str]]:
        """
        从 Claude LLM 生成响应。
        """
        payload = self._build_payload(prompt, stream)

        if stream:
            # 对于流式请求，我们需要一个不同的方式来处理响应
            response = self._client.stream("POST", "/messages", json=payload)
            return self._process_stream_response(response)
        else:
            response = self._request(payload)
            data = response.json()
            # 在非流式响应中，内容位于 content 列表的第一个元素的 text 字段
            return data.get("content", [{}])[0].get("text", "")
