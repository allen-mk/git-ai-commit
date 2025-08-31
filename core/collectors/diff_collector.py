import subprocess
from typing import Any, Mapping

from core.contracts.collector import Collector
from core.registry import collector_registry
from utils.errors import CollectorError


@collector_registry.register("diff")
class DiffCollector(Collector):
    """
    A collector that retrieves the staged changes from a Git repository.
    """

    def __init__(self, staged_only: bool = True, detect_functions: bool = False):
        self.staged_only = staged_only
        self.detect_functions = detect_functions

    def collect(self) -> Mapping[str, Any]:
        """
        Executes `git diff --cached` to get the staged changes.

        Returns:
            A mapping containing the git diff output.

        Raises:
            CollectorError: If the git command fails.
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if result.returncode != 0 and result.returncode != 1:
                 raise CollectorError(f"Failed to get git diff: {result.stderr}")

            return {"diff": result.stdout}
        except FileNotFoundError:
            raise CollectorError("Git is not installed or not in PATH.")
        except subprocess.CalledProcessError as e:
            raise CollectorError(f"Failed to get git diff: {e.stderr}") from e
