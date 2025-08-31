import pytest
import httpx
from typing import List

from config.models import ModelConfig
from core.llm.router import get_provider
from core.llm.providers.openai import OpenAIProvider
from utils.errors import ProviderError


@pytest.fixture
def openai_config():
    return ModelConfig(
        provider="openai",
        name="gpt-4o-mini",
        api_key="test_api_key"
    )

def test_get_provider_openai(openai_config):
    """Tests that the router returns an OpenAIProvider instance."""
    provider = get_provider(openai_config)
    assert isinstance(provider, OpenAIProvider)

def test_get_provider_unknown():
    """Tests that the router raises an error for an unknown provider."""
    config = ModelConfig(provider="unknown")
    with pytest.raises(ProviderError, match="Unknown provider 'unknown'"):
        get_provider(config)

def test_openai_provider_init_no_api_key(mocker):
    """Tests that the provider raises an error if no API key is provided."""
    mocker.patch("os.getenv", return_value=None)
    config = ModelConfig(provider="openai", api_key=None)
    with pytest.raises(ProviderError, match="OpenAI API key not found"):
        OpenAIProvider(config)

def test_openai_provider_generate_non_stream(openai_config, mocker):
    """Tests the non-streaming generate method."""
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello, world!"}}]
    }

    mock_post = mocker.patch("httpx.Client.post", return_value=mock_response)

    provider = OpenAIProvider(openai_config)
    result = provider.generate("Say hi")

    assert result == "Hello, world!"
    mock_post.assert_called_once()
    call_args = mock_post.call_args[1]['json']
    assert call_args['model'] == "gpt-4o-mini"
    assert call_args['stream'] is False

def test_openai_provider_generate_stream(openai_config, mocker):
    """Tests the streaming generate method."""
    chunks = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n',
        'data: {"choices": [{"delta": {"content": ", "}}]}\n\n',
        'data: {"choices": [{"delta": {"content": "world!"}}]}\n\n',
        'data: [DONE]\n\n'
    ]

    def iter_bytes(chunks: List[str]):
        for chunk in chunks:
            yield chunk.encode('utf-8')

    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.iter_lines.return_value = chunks

    # We need to mock the context manager part of the stream
    mock_stream = mocker.patch("httpx.Client.stream", return_value=mock_response)

    provider = OpenAIProvider(openai_config)
    stream_result = provider.generate("Say hi", stream=True)

    result = list(stream_result)
    assert result == ["Hello", ", ", "world!"]
    mock_stream.assert_called_once()
    call_args = mock_stream.call_args[1]['json']
    assert call_args['stream'] is True

def test_openai_provider_http_error(openai_config, mocker):
    """Tests that a ProviderError is raised on HTTP status errors."""
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.json.return_value = {"error": {"message": "Invalid API key"}}

    http_error = httpx.HTTPStatusError(
        "Unauthorized", request=mocker.MagicMock(), response=mock_response
    )
    mocker.patch("httpx.Client.post", side_effect=http_error)

    provider = OpenAIProvider(openai_config)
    with pytest.raises(ProviderError, match="OpenAI API error \\(401\\): Invalid API key"):
        provider.generate("Say hi")

def test_openai_provider_timeout_error(openai_config, mocker):
    """Tests that a ProviderError is raised on timeout."""
    mocker.patch("httpx.Client.post", side_effect=httpx.TimeoutException("Timeout!"))

    provider = OpenAIProvider(openai_config)
    with pytest.raises(ProviderError, match="Request to OpenAI timed out: Timeout!"):
        provider.generate("Say hi")
