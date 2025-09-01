from typing import Any, Mapping

from core.contracts.collector import Collector
from core.registry import collector_registry
from utils.errors import CollectorError
from utils.git import get_staged_diff


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
            diff = get_staged_diff()
            return {"diff": diff}
        except Exception as e:
            raise CollectorError(f"Failed to collect git diff: {e}") from e
