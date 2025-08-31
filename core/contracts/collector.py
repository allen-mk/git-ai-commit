from typing import Any, Mapping, Protocol


class Collector(Protocol):
    """A protocol for classes that collect information."""

    def collect(self) -> Mapping[str, Any]:
        """Collects information and returns it as a mapping."""
        ...
