import unittest
from pathlib import Path
from unittest.mock import MagicMock

from core.contracts.models import Context
from core.formatter.jinja_formatter import Jinja2Formatter
from utils.errors import FormatterError


class TestJinja2Formatter(unittest.TestCase):
    def setUp(self):
        # Create a dummy context for testing
        self.ctx = Context(
            files=[],
            readme="This is a test readme.",
            recent_commits=["feat: initial commit"],
            meta={"branch": "main"},
        )
        self.model_output = "feat: add new feature\n\nThis is a great new feature."

    def test_format_conventional(self):
        # Test with the conventional template
        formatter = Jinja2Formatter(template_name="conventional.j2")
        formatted_message = formatter.format(self.ctx, self.model_output)
        self.assertEqual(formatted_message, self.model_output)

    def test_format_simple(self):
        # Test with the simple template
        formatter = Jinja2Formatter(template_name="simple.j2")
        formatted_message = formatter.format(self.ctx, self.model_output)
        self.assertEqual(formatted_message, self.model_output)

    def test_template_not_found(self):
        # Test for template not found error
        formatter = Jinja2Formatter(template_name="non_existent_template.j2")
        with self.assertRaises(FormatterError):
            formatter.format(self.ctx, self.model_output)

    def test_custom_template_dir(self):
        # Test with a custom template directory
        custom_template_dir = Path("./tests/custom_templates")
        custom_template_dir.mkdir(exist_ok=True)
        custom_template_path = custom_template_dir / "custom.j2"
        with open(custom_template_path, "w") as f:
            f.write("Custom: {{ model_output }}")

        formatter = Jinja2Formatter(
            template_dir=str(custom_template_dir), template_name="custom.j2"
        )
        formatted_message = formatter.format(self.ctx, self.model_output)
        self.assertEqual(formatted_message, f"Custom: {self.model_output}")

        # Clean up the custom template
        custom_template_path.unlink()
        custom_template_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
