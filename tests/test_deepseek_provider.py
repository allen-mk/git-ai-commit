import pytest
import httpx
from typing import List

from config.models import ModelConfig
from core.llm.router import get_provider
from core.llm.providers.deepseek import DeepSeekProvider
from utils.errors import ProviderError


@pytest.fixture
def deepseek_config():
    """Fixture for DeepSeek provider configuration."""
    return ModelConfig(
        provider="deepseek",
        name="deepseek-chat",
        api_key="test_deepseek_api_key"
    )

def test_get_provider_deepseek(deepseek_config):
    """Tests that the router returns a DeepSeekProvider instance."""
    provider = get_provider(deepseek_config)
    assert isinstance(provider, DeepSeekProvider)

def test_deepseek_provider_init_no_api_key(mocker):
    """Tests that the provider raises an error if no API key is provided."""
    mocker.patch("os.getenv", return_value=None)
    config = ModelConfig(provider="deepseek", api_key=None)
    with pytest.raises(ProviderError, match="DeepSeek API key not found"):
        DeepSeekProvider(config)

def test_deepseek_provider_generate_non_stream(deepseek_config, mocker):
    """Tests the non-streaming generate method for DeepSeek."""
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello from DeepSeek!"}}]
    }

    mock_post = mocker.patch("httpx.Client.post", return_value=mock_response)

    provider = DeepSeekProvider(deepseek_config)
    result = provider.generate("Say hi")

    assert result == "Hello from DeepSeek!"
    mock_post.assert_called_once()
    call_args = mock_post.call_args[1]['json']
    assert call_args['model'] == "deepseek-chat"
    assert call_args['stream'] is False

def test_deepseek_provider_generate_stream(deepseek_config, mocker):
    """Tests the streaming generate method for DeepSeek."""
    chunks = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n',
        'data: {"choices": [{"delta": {"content": " from"}}]}\n\n',
        'data: {"choices": [{"delta": {"content": " DeepSeek!"}}]}\n\n',
        'data: [DONE]\n\n'
    ]

    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.iter_lines.return_value = chunks

    mock_stream = mocker.patch("httpx.Client.stream", return_value=mock_response)

    provider = DeepSeekProvider(deepseek_config)
    stream_result = provider.generate("Say hi", stream=True)

    result = list(stream_result)
    assert result == ["Hello", " from", " DeepSeek!"]
    mock_stream.assert_called_once()
    call_args = mock_stream.call_args[1]['json']
    assert call_args['stream'] is True

def test_deepseek_provider_http_error(deepseek_config, mocker):
    """Tests that a ProviderError is raised on HTTP status errors for DeepSeek."""
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.json.return_value = {"error": {"message": "Invalid API key"}}

    http_error = httpx.HTTPStatusError(
        "Unauthorized", request=mocker.MagicMock(), response=mock_response
    )
    mocker.patch("httpx.Client.post", side_effect=http_error)

    provider = DeepSeekProvider(deepseek_config)
    with pytest.raises(ProviderError, match="DeepSeek API error \\(401\\): Invalid API key"):
        provider.generate("Say hi")

def test_deepseek_provider_timeout_error(deepseek_config, mocker):
    """Tests that a ProviderError is raised on timeout for DeepSeek."""
    mocker.patch("httpx.Client.post", side_effect=httpx.TimeoutException("Timeout!"))

    provider = DeepSeekProvider(deepseek_config)
    with pytest.raises(ProviderError, match="Request to DeepSeek timed out: Timeout!"):
        provider.generate("Say hi")
