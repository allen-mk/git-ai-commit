import pytest
import httpx

from config.models import ModelConfig
from core.llm.router import get_provider
from core.llm.providers.local import LocalProvider
from utils.errors import ProviderError

@pytest.fixture
def local_config():
    """Fixture for Local provider configuration."""
    return ModelConfig(
        provider="local",
        name="llama3",
        base_url="http://localhost:11434/v1",
        api_key="ollama" # Ollama uses "ollama" as a default key
    )

def test_get_provider_local(local_config):
    """Tests that the router returns a LocalProvider instance."""
    provider = get_provider(local_config)
    assert isinstance(provider, LocalProvider)

def test_local_provider_init_no_base_url():
    """Tests that the provider raises an error if no base_url is provided."""
    config = ModelConfig(provider="local", base_url=None)
    with pytest.raises(ProviderError, match="Local provider requires a `base_url`"):
        LocalProvider(config)

def test_local_provider_init_no_api_key(local_config):
    """Tests that the provider can be initialized without an explicit API key."""
    local_config.api_key = None
    # This should not raise an error
    provider = LocalProvider(local_config)
    assert provider is not None

def test_local_provider_generate_non_stream(local_config, mocker):
    """Tests the non-streaming generate method for the Local provider."""
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello from Local LLM!"}}]
    }

    mock_post = mocker.patch("httpx.Client.post", return_value=mock_response)

    provider = LocalProvider(local_config)
    result = provider.generate("Say hi")

    assert result == "Hello from Local LLM!"
    mock_post.assert_called_once()
    call_args = mock_post.call_args[1]['json']
    assert call_args['model'] == "llama3"
    assert call_args['stream'] is False

def test_local_provider_generate_stream(local_config, mocker):
    """Tests the streaming generate method for the Local provider."""
    chunks = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n',
        'data: {"choices": [{"delta": {"content": " from"}}]}\n\n',
        'data: {"choices": [{"delta": {"content": " Local LLM!"}}]}\n\n',
        'data: [DONE]\n\n'
    ]

    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.iter_lines.return_value = chunks

    mock_stream = mocker.patch("httpx.Client.stream", return_value=mock_response)

    provider = LocalProvider(local_config)
    stream_result = provider.generate("Say hi", stream=True)

    result = list(stream_result)
    assert result == ["Hello", " from", " Local LLM!"]
    mock_stream.assert_called_once()
    call_args = mock_stream.call_args[1]['json']
    assert call_args['stream'] is True

def test_local_provider_network_error(local_config, mocker):
    """Tests that a ProviderError is raised on network errors for the Local provider."""
    mocker.patch("httpx.Client.post", side_effect=httpx.RequestError("Connection failed"))

    provider = LocalProvider(local_config)
    with pytest.raises(ProviderError, match="An unexpected network error occurred with the local provider"):
        provider.generate("Say hi")
