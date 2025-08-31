import os
from typing import Any, Mapping

from core.contracts.collector import Collector
from core.registry import collector_registry


@collector_registry.register("readme")
class ReadmeCollector(Collector):
    """
    A collector that retrieves the content of the project's README file.
    """

    def collect(self) -> Mapping[str, Any]:
        """
        Finds and reads README.md or README.rst from the project root.

        Returns:
            A mapping containing the README content, or an empty string if not found.
        """
        readme_content = ""
        for filename in ["README.md", "README.rst"]:
            if os.path.exists(filename):
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        readme_content = f.read()
                    break
                except Exception:
                    # If reading fails, we can either log this or just continue.
                    # For now, we'll just try the next file.
                    continue

        return {"readme": readme_content}
