import subprocess
from typing import Any, List, Mapping

from core.contracts.collector import Collector
from core.registry import collector_registry
from utils.errors import CollectorError


@collector_registry.register("history")
class HistoryCollector(Collector):
    """
    A collector that retrieves the recent commit history from a Git repository.
    """

    def __init__(self, n: int = 10):
        """
        Initializes the HistoryCollector.

        Args:
            n: The number of recent commits to retrieve.
        """
        if n <= 0:
            raise ValueError("Number of commits (n) must be a positive integer.")
        self._n = n

    def collect(self) -> Mapping[str, Any]:
        """
        Executes `git log -n <n> --pretty=%B` to get recent commit messages.

        Returns:
            A mapping containing a list of commit messages.

        Raises:
            CollectorError: If the git command fails.
        """
        try:
            # Git log format %B%x00 separates commit messages with a null byte.
            command = ["git", "log", f"-n{self._n}", "--pretty=%B%x00"]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
            )
            commits = result.stdout.strip("\x00").split("\x00")
            return {"history": [commit.strip() for commit in commits if commit.strip()]}
        except FileNotFoundError:
            raise CollectorError("Git is not installed or not in PATH.")
        except subprocess.CalledProcessError as e:
            # If the repository is empty, it might raise an error.
            if "does not have any commits" in e.stderr:
                return {"history": []}
            raise CollectorError(f"Failed to get git history: {e.stderr}") from e
