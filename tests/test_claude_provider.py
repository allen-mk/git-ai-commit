import pytest
import httpx
from typing import List

from config.models import ModelConfig
from core.llm.router import get_provider
from core.llm.providers.claude import ClaudeProvider
from utils.errors import ProviderError


@pytest.fixture
def claude_config():
    """Fixture for Claude provider configuration."""
    return ModelConfig(
        provider="claude",
        name="claude-3-opus-20240229",
        api_key="test_claude_api_key"
    )

def test_get_provider_claude(claude_config):
    """Tests that the router returns a ClaudeProvider instance."""
    provider = get_provider(claude_config)
    assert isinstance(provider, ClaudeProvider)

def test_claude_provider_init_no_api_key(mocker):
    """Tests that the provider raises an error if no API key is provided."""
    mocker.patch("os.getenv", return_value=None)
    config = ModelConfig(provider="claude", api_key=None)
    with pytest.raises(ProviderError, match="Anthropic API key not found"):
        ClaudeProvider(config)

@pytest.mark.asyncio
async def test_claude_provider_generate_non_stream(claude_config, mocker):
    """Tests the non-streaming generate method for Claude."""
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "Hello from Claude!"}]
    }

    mock_post = mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    provider = ClaudeProvider(claude_config)
    result = await provider.generate("Say hi")

    assert result == "Hello from Claude!"
    mock_post.assert_called_once()
    call_args = mock_post.call_args[1]['json']
    assert call_args['model'] == "claude-3-opus-20240229"
    assert call_args['stream'] is False
    assert call_args['max_tokens'] == 4096

@pytest.mark.asyncio
async def test_claude_provider_generate_stream(claude_config, mocker):
    """Tests the streaming generate method for Claude."""
    chunks = [
        'event: message_start\ndata: {"type": "message_start", "message": {"id": "msg_123", "role": "assistant"}}',
        'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}',
        'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": " from"}}',
        'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": " Claude!"}}',
        'event: message_stop\ndata: {"type": "message_stop", "stop_reason": "end_turn"}'
    ]

    async def aiter_lines():
        for chunk in "\n".join(chunks).splitlines():
            yield chunk

    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.aiter_lines.return_value = aiter_lines()

    # Create an async context manager mock
    async_mock_context = mocker.AsyncMock()
    async_mock_context.__aenter__.return_value = mock_response

    mock_stream = mocker.patch("httpx.AsyncClient.stream", return_value=async_mock_context)

    provider = ClaudeProvider(claude_config)
    stream_result = await provider.generate("Say hi", stream=True)

    result = [chunk async for chunk in stream_result]
    assert result == ["Hello", " from", " Claude!"]
    mock_stream.assert_called_once()
    call_args = mock_stream.call_args[1]['json']
    assert call_args['stream'] is True

@pytest.mark.asyncio
async def test_claude_provider_http_error(claude_config, mocker):
    """Tests that a ProviderError is raised on HTTP status errors for Claude."""
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_response.json.return_value = {"error": {"type": "invalid_request_error", "message": "Malformed request"}}

    http_error = httpx.HTTPStatusError(
        "Bad Request", request=mocker.MagicMock(), response=mock_response
    )
    mocker.patch("httpx.AsyncClient.post", side_effect=http_error)

    provider = ClaudeProvider(claude_config)
    with pytest.raises(ProviderError, match="Anthropic API error \\(400\\): Malformed request"):
        await provider.generate("Say hi")

@pytest.mark.asyncio
async def test_claude_provider_timeout_error(claude_config, mocker):
    """Tests that a ProviderError is raised on timeout for Claude."""
    mocker.patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout!"))

    provider = ClaudeProvider(claude_config)
    with pytest.raises(ProviderError, match="Request to Anthropic timed out: Timeout!"):
        await provider.generate("Say hi")
