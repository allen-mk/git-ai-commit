from typing import Protocol
from .models import Context

class Formatter(Protocol):
    def format(self, ctx: Context, model_output: str) -> str:
        ...
