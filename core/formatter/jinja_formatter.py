import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from core.contracts.formatter import Formatter
from core.contracts.models import Context
from utils.errors import FormatterError


class Jinja2Formatter(Formatter):
    def __init__(
        self,
        template_dir: Optional[str] = None,
        template_name: str = "conventional.j2",
    ):
        if template_dir is None:
            # Default template directory relative to this file
            template_dir = str(Path(__file__).parent / "templates")

        self.template_dir = template_dir
        self.template_name = template_name
        try:
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        except Exception as e:
            raise FormatterError(f"Failed to initialize Jinja2 environment: {e}") from e

    def format(self, ctx: Context, model_output: str) -> str:
        try:
            template = self.env.get_template(self.template_name)
            return template.render(
                ctx=ctx,
                model_output=model_output,
                now=datetime.datetime.now,
            )
        except Exception as e:
            raise FormatterError(f"Failed to render template {self.template_name}: {e}") from e
