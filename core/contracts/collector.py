from typing import Protocol, Mapping, Any

class Collector(Protocol):
    def collect(self) -> Mapping[str, Any]:
        ...
