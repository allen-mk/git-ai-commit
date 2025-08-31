import asyncio
from typing import Any, Dict, List, Mapping, Union

from config.models import Config
from core.contracts.collector import Collector
from core.contracts.formatter import Formatter
from core.contracts.models import Context
from core.contracts.provider import LLMProvider
from core.formatter.jinja_formatter import Jinja2Formatter
from core.registry import collector_registry, provider_registry
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

    async def generate(self) -> str:
        """
        Generates a commit message by running the full pipeline.

        Returns:
            The generated commit message.
        """
        logger.info("Starting commit message generation pipeline...")

        # 1. Collect context
        try:
            context_data = await self._collect_context()
            logger.info(f"Collected context data: {list(context_data.keys())}")
        except CollectorError as e:
            logger.error(f"Failed to collect context: {e}", exc_info=True)
            # Depending on desired behavior, we might return a default message or re-raise
            return f"Error: Could not collect context. {e}"

        context = self._aggregate_context(context_data)
        logger.debug(f"Aggregated context: {context.model_dump_json(indent=2)}")

        # 2. Generate raw message from LLM
        try:
            raw_message = await self._generate_raw_message(context)
            logger.info("Successfully generated raw message from LLM.")
            logger.debug(f"Raw LLM output:\n{raw_message}")
        except ProviderError as e:
            logger.error(f"Failed to generate message from provider: {e}", exc_info=True)
            return f"Error: Could not generate message. {e}"

        # 3. Format the final message
        try:
            formatted_message = self._format_message(context, raw_message)
            logger.info("Successfully formatted the commit message.")
        except FormatterError as e:
            logger.error(f"Failed to format message: {e}", exc_info=True)
            return f"Error: Could not format message. {e}"

        logger.success("Commit message generation pipeline completed successfully!")
        return formatted_message

    async def _collect_context(self) -> Dict[str, Any]:
        """
        Runs all configured collectors to gather context.
        """
        logger.info(f"Running {len(self.config.collectors)} collectors...")
        tasks = []
        for collector_config in self.config.collectors:
            try:
                # Instantiate collector
                collector_cls = collector_registry.get(collector_config.type)
                collector: Collector = collector_cls(**collector_config.options)

                # Run async if possible, otherwise run in thread pool
                if asyncio.iscoroutinefunction(collector.collect):
                    tasks.append(asyncio.create_task(collector.collect()))
                else:
                    tasks.append(asyncio.to_thread(collector.collect))
            except KeyError:
                raise CollectorError(f"Collector '{collector_config.type}' not found in registry.")
            except Exception as e:
                raise CollectorError(f"Failed to instantiate or run collector '{collector_config.type}': {e}")

        results: List[Mapping[str, Any]] = await asyncio.gather(*tasks)

        # Merge results into a single dictionary
        combined_data: Dict[str, Any] = {}
        for data in results:
            for key, value in data.items():
                # Simple merge: last one wins. Could be more sophisticated.
                if value: # only merge non-empty values
                    combined_data[key] = value

        return combined_data

    def _aggregate_context(self, context_data: Dict[str, Any]) -> Context:
        """
        Aggregates data from collectors into a single Context object.
        """
        logger.info("Aggregating collector data into Context object.")
        # Pydantic will automatically validate and map the fields
        return Context(**context_data)

    async def _generate_raw_message(self, context: Context) -> str:
        """
        Generates the raw commit message using the LLM provider.
        """
        logger.info(f"Generating raw message with provider '{self.config.model.provider}'.")
        try:
            provider_cls = provider_registry.get(self.config.model.provider)
            provider: LLMProvider = provider_cls(
                model_name=self.config.model.name,
                api_key=self.config.model.api_key,
                timeout=self.config.model.timeout_sec,
            )
        except KeyError:
            raise ProviderError(f"Provider '{self.config.model.provider}' not found in registry.")
        except Exception as e:
            raise ProviderError(f"Failed to instantiate provider '{self.config.model.provider}': {e}")

        prompt = self._create_prompt(context)
        logger.debug(f"Generated prompt for LLM:\n{prompt}")

        # Assuming generate can be async
        if asyncio.iscoroutinefunction(provider.generate):
            response = await provider.generate(prompt)
        else:
            response = await asyncio.to_thread(provider.generate, prompt)

        if not isinstance(response, str):
            # For now, we'll just join streaming responses.
            # A more advanced implementation would handle this differently.
            return "".join(list(response))
        return response

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
