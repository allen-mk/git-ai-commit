import asyncio
from typing import Any, AsyncGenerator, AsyncIterable, Dict, List, Mapping, Union

from config.models import Config
from core.contracts.collector import Collector
from core.contracts.formatter import Formatter
from core.contracts.models import Context
from core.contracts.provider import LLMProvider
from core.formatter.jinja_formatter import Jinja2Formatter
from core.registry import collector_registry, provider_registry
from utils.cache import Cache
from utils.errors import CollectorError, FormatterError, ProviderError
from utils.logger import logger


class CommitMessageGenerator:
    """
    The main pipeline for generating commit messages.
    It orchestrates the collection, generation, and formatting steps.
    """

    def __init__(self, config: Config):
        """
        Initializes the pipeline with the given configuration.

        Args:
            config: The configuration object.
        """
        self.config = config
        self.cache = Cache(
            cache_dir=self.config.cache.directory,
            ttl_sec=self.config.cache.ttl_sec
        ) if self.config.cache.enabled else None

    async def generate(self, stream: bool = False) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generates a commit message by running the full pipeline.

        Args:
            stream: Whether to stream the response from the provider.

        Returns:
            If streaming, an async generator of message chunks.
            If not streaming, the complete, formatted commit message as a string.
        """
        logger.info("Starting commit message generation pipeline...")
        # 1. Collect context (applies to both modes)
        try:
            context_data = await self._collect_context()
            logger.info(f"Collected context data: {list(context_data.keys())}")
        except CollectorError as e:
            logger.error(f"Failed to collect context: {e}", exc_info=True)
            raise  # Re-raise to be handled by the CLI

        context = self._aggregate_context(context_data)
        logger.debug(f"Aggregated context: {context.model_dump_json(indent=2)}")

        # 2. Generate raw message from LLM (with caching)
        try:
            raw_message_or_stream = await self._generate_raw_message(context, stream=stream)
        except ProviderError as e:
            logger.error(f"Failed to generate message from provider: {e}", exc_info=True)
            raise

        # 3. Handle streaming vs. non-streaming output
        if stream:
            # The CLI is responsible for consuming this generator
            return raw_message_or_stream
        else:
            # 4. Format the final message for non-streaming mode
            try:
                formatted_message = self._format_message(context, raw_message_or_stream)
                logger.info("Successfully formatted the commit message.")
                logger.success("Commit message generation pipeline completed successfully!")
                return formatted_message
            except FormatterError as e:
                logger.error(f"Failed to format message: {e}", exc_info=True)
                raise

    async def _collect_context(self) -> Dict[str, Any]:
        """
        Runs all configured collectors to gather context.
        """
        logger.info(f"Running {len(self.config.collectors)} collectors...")
        tasks = []
        for collector_config in self.config.collectors:
            try:
                collector_cls = collector_registry.get(collector_config.type)
                collector: Collector = collector_cls(**collector_config.options)
                if asyncio.iscoroutinefunction(collector.collect):
                    tasks.append(asyncio.create_task(collector.collect()))
                else:
                    tasks.append(asyncio.to_thread(collector.collect))
            except KeyError:
                raise CollectorError(f"Collector '{collector_config.type}' not found in registry.")
            except Exception as e:
                raise CollectorError(f"Failed to instantiate or run collector '{collector_config.type}': {e}")

        results: List[Mapping[str, Any]] = await asyncio.gather(*tasks)

        combined_data: Dict[str, Any] = {}
        for data in results:
            for key, value in data.items():
                if value:
                    combined_data[key] = value
        return combined_data

    def _aggregate_context(self, context_data: Dict[str, Any]) -> Context:
        """
        Aggregates data from collectors into a single Context object.
        """
        logger.info("Aggregating collector data into Context object.")
        return Context(**context_data)

    async def _call_provider(self, context: Context, stream: bool) -> Union[str, AsyncIterable[str]]:
        """The actual logic to call the LLM provider."""
        logger.info(f"Calling LLM provider '{self.config.model.provider}'...")
        try:
            provider_cls = provider_registry.get(self.config.model.provider)
            provider: LLMProvider = provider_cls(config=self.config.model)
        except KeyError:
            raise ProviderError(f"Provider '{self.config.model.provider}' not found in registry.")
        except Exception as e:
            raise ProviderError(f"Failed to instantiate provider '{self.config.model.provider}': {e}")

        prompt = self._create_prompt(context)
        logger.debug(f"Generated prompt for LLM:\n{prompt}")

        response = await provider.generate(prompt, stream=stream)
        return response

    async def _generate_raw_message(self, context: Context, stream: bool = False) -> Union[str, AsyncIterable[str]]:
        """
        Generates the raw commit message using the LLM provider, with caching.
        Caching is bypassed for streaming requests.
        """
        if stream or not self.cache or not self.cache.is_enabled():
            return await self._call_provider(context, stream)

        # Create a stable string from the diffs to use as a cache key.
        # It's important that this is deterministic.
        if not context.files:
            # If there are no files, we can't generate a diff-based cache key.
            return await self._call_provider(context, stream=False)

        diff_content = "\n---\n".join(sorted(f.diff for f in context.files))

        cached_message = self.cache.get(diff_content)
        if cached_message:
            logger.info("Cache hit. Returning cached raw message.")
            return cached_message

        logger.info("Cache miss. Calling provider to generate new message.")
        raw_message = await self._call_provider(context, stream=False)

        if isinstance(raw_message, str):
            self.cache.set(diff_content, raw_message)

        return raw_message

    def _format_message(self, context: Context, model_output: str) -> str:
        """
        Formats the raw model output into the final commit message.
        """
        logger.info("Formatting final commit message.")
        # For now, we only have one formatter type, so we instantiate it directly.
        # This could be extended to use a registry if more formatters are added.
        formatter: Formatter = Jinja2Formatter(
            template_dir=self.config.formatter.template_dir,
            template_name=self.config.formatter.template,
        )
        return formatter.format(context, model_output)

    def _create_prompt(self, context: Context) -> str:
        """
        Creates the prompt to be sent to the LLM.
        """
        # This is a basic prompt template. It could be moved to a configuration file
        # or a more sophisticated templating system in the future.

        prompt_template = """
You are an expert at writing git commit messages.
Your task is to write a commit message for the following changes.

The commit message must follow the Conventional Commits specification.
The output language should be {language}.

Here is the context for the changes:
{context_summary}

And here are the file-by-file changes (diffs):
{diffs}

Please generate a concise and informative commit message.
Do not include any extra text or explanations, only the commit message itself.
"""

        context_summary_parts = []
        if context.readme:
            context_summary_parts.append(f"README Summary:\n{context.readme[:500]}...") # Truncate for prompt
        if context.recent_commits:
            commits_str = "\n".join(f"- {c}" for c in context.recent_commits)
            context_summary_parts.append(f"Recent Commits:\n{commits_str}")
        if context.issues:
            issues_str = "\n".join(f"- {i.get('title', 'N/A')}" for i in context.issues)
            context_summary_parts.append(f"Related Issues:\n{issues_str}")

        context_summary = "\n\n".join(context_summary_parts)

        diffs = "\n\n".join(
            f"File: {file.path}\n```diff\n{file.diff}\n```"
            for file in context.files
        )

        return prompt_template.format(
            language=self.config.output.language,
            context_summary=context_summary if context_summary_parts else "No additional context provided.",
            diffs=diffs
        )
