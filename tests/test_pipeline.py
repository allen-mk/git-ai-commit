import asyncio
import unittest
from unittest.mock import patch

from config.models import CacheConfig, CollectorConfig, Config, FormatterConfig, ModelConfig
from core.contracts.models import Context, FileChange
from core.pipeline import CommitMessageGenerator


# Mock the registries
@patch("core.pipeline.collector_registry")
@patch("core.pipeline.provider_registry")
class TestCommitMessageGenerator(unittest.TestCase):
    def setUp(self):
        # Dummy components for testing
        class DummyCollector:
            def collect(self):
                return {
                    "files": [FileChange(path="a.txt", diff="+a")],
                    "readme": "Dummy readme",
                }

        class DummyProvider:
            def __init__(self, *args, **kwargs):
                pass

            async def generate(self, prompt: str, *, stream: bool = False) -> str:
                return "feat: dummy feature"

        self.dummy_collector = DummyCollector
        self.dummy_provider = DummyProvider

        # Mock config to use dummy components
        self.config = Config(
            model=ModelConfig(provider="dummy"),
            formatter=FormatterConfig(template="simple.j2"),
            collectors=[CollectorConfig(type="dummy")],
            cache=CacheConfig(enabled=False)  # Disable cache for testing
        )

    def test_generate_end_to_end(self, mock_provider_registry, mock_collector_registry):
        """
        Tests the full pipeline from collection to formatting.
        """
        # Configure mocks
        mock_collector_registry.get.return_value = self.dummy_collector
        mock_provider_registry.get.return_value = self.dummy_provider

        # Instantiate the generator
        generator = CommitMessageGenerator(config=self.config)

        # Run the pipeline
        result = asyncio.run(generator.generate())

        # Assertions
        mock_collector_registry.get.assert_called_once_with("dummy")
        mock_provider_registry.get.assert_called_once_with("dummy")

        # The simple.j2 template just returns the model output directly
        self.assertEqual(result, "feat: dummy feature")

    def test_prompt_creation(self, mock_provider_registry, mock_collector_registry):
        """
        Tests if the prompt is created correctly based on context.
        """
        # Configure mocks
        mock_collector_registry.get.return_value = self.dummy_collector
        mock_provider_registry.get.return_value = self.dummy_provider

        generator = CommitMessageGenerator(config=self.config)

        context = Context(
            files=[FileChange(path="a.txt", diff="+a")],
            readme="Test readme.",
            recent_commits=["fix: bug #123"]
        )

        prompt = generator._create_prompt(context)

        self.assertIn("The output language should be en.", prompt)
        self.assertIn("README Summary:\nTest readme.", prompt)
        self.assertIn("Recent Commits:\n- fix: bug #123", prompt)
        self.assertIn("File: a.txt\n```diff\n+a\n```", prompt)


if __name__ == "__main__":
    unittest.main()
