import asyncio
import click
from rich.console import Console
from rich.panel import Panel
from rich.status import Status

# Import collectors and providers to register them
import core.collectors
import core.llm.providers

from config.logic import load_and_merge_configs
from config.models import Config
from core.pipeline import CommitMessageGenerator
from utils.errors import AICommitException
from utils.logger import setup_logger, logger
from utils.git import is_git_repository, has_staged_changes, commit


def apply_cli_overrides(config: Config, provider: str, model: str, template: str) -> Config:
    """Applies CLI options to the loaded configuration."""
    if provider:
        config.model.provider = provider
        logger.info(f"Overriding provider with: {provider}")
    if model:
        config.model.name = model
        logger.info(f"Overriding model with: {model}")
    if template:
        config.formatter.template = template
        logger.info(f"Overriding template with: {template}")
    return config


async def run_generation(config: Config) -> str:
    """
    Initializes and runs the commit message generation pipeline.
    """
    pipeline = CommitMessageGenerator(config)
    return await pipeline.generate()


@click.command()
@click.option(
    "-c", "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a custom configuration file.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Generate the commit message but do not apply it.",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Enable verbose logging for debugging.",
)
@click.option("--provider", type=str, help="Override the LLM provider (e.g., 'openai').")
@click.option("--model", type=str, help="Override the LLM model name (e.g., 'gpt-4o-mini').")
@click.option("--template", type=str, help="Override the template file to use.")
def main(config_path: str, dry_run: bool, verbose: bool, provider: str, model: str, template: str):
    """
    AI-powered Git commit message generator.
    """
    console = Console()
    setup_logger(log_level="DEBUG" if verbose else "INFO")

    try:
        # 0. Pre-checks
        if not is_git_repository():
            raise AICommitException("Not a Git repository. Please run this command from the root of a Git repository.")
        if not has_staged_changes():
            raise AICommitException("No staged changes found. Please stage your changes before running.")

        # 1. Load configuration
        config = load_and_merge_configs(custom_config_path=config_path)

        # 2. Apply CLI overrides
        config = apply_cli_overrides(config, provider, model, template)

        # 3. Run pipeline
        message = ""
        with console.status("[bold green]Generating commit message...[/bold green]") as status:
            try:
                message = asyncio.run(run_generation(config))
            except Exception as e:
                logger.error(f"Failed during message generation: {e}", exc_info=verbose)
                # Re-raise as our custom exception to be caught by the outer block
                raise AICommitException(f"Failed during message generation: {e}")


        # 4. Display result
        console.print(Panel(
            message,
            title="[bold cyan]Generated Commit Message[/bold cyan]",
            border_style="cyan",
            expand=False,
        ))

        if not dry_run:
            commit(message)
            console.print("\n[bold green]✅ Commit successful![/bold green]")
        else:
            console.print("\n[yellow]Dry run is enabled. To apply the commit, run without the `--dry-run` flag.[/yellow]")

    except AICommitException as e:
        # Log the full error if verbose, but only show the user-friendly message
        logger.error(f"A known error occurred: {e}", exc_info=verbose)
        console.print(f"[bold red]Error:[/bold red] {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")


if __name__ == "__main__":
    main()
