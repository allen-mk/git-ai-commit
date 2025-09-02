import os
import httpx
import json
from typing import Iterable, Union, Generator

from core.contracts.provider import LLMProvider
from config.models import ModelConfig
from core.registry import provider_registry
from utils.errors import ProviderError

@provider_registry.register("local")
class LocalProvider(LLMProvider):
    """
    一个用于本地 OpenAI 兼容 API (如 Ollama) 的 Provider。
    """

    def __init__(self, config: ModelConfig):
        self.config = config

        # 本地服务通常不需要 API 密钥，但如果提供了，我们还是会使用它
        self._api_key = config.api_key or os.getenv("LOCAL_API_KEY", "ollama") # 默认一个非空值

        # 获取 base_url，如果未提供则报错
        self._base_url = config.base_url or os.getenv("OLLAMA_BASE_URL")
        if not self._base_url:
            raise ProviderError("Local provider requires a `base_url` to be set in the config.")

        # 初始化 httpx 客户端
        self._client = httpx.Client(
            base_url=self._base_url,
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
            # 路径通常是 /chat/completions
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise ProviderError(f"Request to local provider timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            try:
                error_details = e.response.json()
                error_message = error_details.get("error", {}).get("message", e.response.text)
            except json.JSONDecodeError:
                error_message = e.response.text
            raise ProviderError(f"Local provider API error ({e.response.status_code}): {error_message}") from e
        except httpx.RequestError as e:
            raise ProviderError(f"An unexpected network error occurred with the local provider: {e}") from e

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
        从本地 LLM 生成响应。
        """
        payload = self._build_payload(prompt, stream)

        if stream:
            response = self._client.stream("POST", "/chat/completions", json=payload)
            return self._process_stream_response(response)
        else:
            response = self._request(payload)
            data = response.json()
            return data["choices"][0]["message"]["content"]
