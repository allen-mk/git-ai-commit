import subprocess
import unittest
from unittest.mock import MagicMock, mock_open, patch

from core.collectors.diff_collector import DiffCollector
from core.collectors.history_collector import HistoryCollector
from core.collectors.readme_collector import ReadmeCollector
from utils.errors import CollectorError


class TestDiffCollector(unittest.TestCase):

    @patch("subprocess.run")
    def test_collect_with_staged_changes(self, mock_run):
        # Arrange
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = "diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,1 @@\n-hello\n+world"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        collector = DiffCollector()

        # Act
        result = collector.collect()

        # Assert
        self.assertEqual(result, {"diff": mock_process.stdout})
        mock_run.assert_called_once_with(
            ["git", "diff", "--cached"], capture_output=True, text=True, encoding="utf-8"
        )

    @patch("subprocess.run")
    def test_collect_no_staged_changes(self, mock_run):
        # Arrange
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        collector = DiffCollector()

        # Act
        result = collector.collect()

        # Assert
        self.assertEqual(result, {"diff": ""})

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_collect_git_not_found(self, mock_run):
        # Arrange
        collector = DiffCollector()

        # Act & Assert
        with self.assertRaises(CollectorError) as cm:
            collector.collect()
        self.assertIn("Git is not installed", str(cm.exception))

    @patch("subprocess.run")
    def test_collect_git_error(self, mock_run):
        # Arrange
        mock_process = MagicMock()
        mock_process.returncode = 128
        mock_process.stderr = "fatal: not a git repository"
        mock_run.return_value = mock_process

        collector = DiffCollector()

        # Act & Assert
        with self.assertRaises(CollectorError) as cm:
            collector.collect()
        self.assertIn("Failed to get git diff", str(cm.exception))


class TestReadmeCollector(unittest.TestCase):

    @patch("os.path.exists", side_effect=lambda f: f == "README.md")
    @patch("builtins.open", new_callable=mock_open, read_data="This is a test README.")
    def test_collect_with_readme_md(self, mock_file, mock_exists):
        # Arrange
        collector = ReadmeCollector()

        # Act
        result = collector.collect()

        # Assert
        self.assertEqual(result, {"readme": "This is a test README."})
        mock_file.assert_called_once_with("README.md", "r", encoding="utf-8")

    @patch("os.path.exists", side_effect=lambda f: f == "README.rst")
    @patch("builtins.open", new_callable=mock_open, read_data="This is a test README in RST.")
    def test_collect_with_readme_rst(self, mock_file, mock_exists):
        # Arrange
        collector = ReadmeCollector()

        # Act
        result = collector.collect()

        # Assert
        self.assertEqual(result, {"readme": "This is a test README in RST."})
        mock_file.assert_called_once_with("README.rst", "r", encoding="utf-8")

    @patch("os.path.exists", return_value=False)
    def test_collect_no_readme_found(self, mock_exists):
        # Arrange
        collector = ReadmeCollector()

        # Act
        result = collector.collect()

        # Assert
        self.assertEqual(result, {"readme": ""})


class TestHistoryCollector(unittest.TestCase):

    @patch("subprocess.run")
    def test_collect_with_history(self, mock_run):
        # Arrange
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "feat: new feature\x00fix: a bug\x00"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        collector = HistoryCollector(n=2)

        # Act
        result = collector.collect()

        # Assert
        self.assertEqual(result, {"history": ["feat: new feature", "fix: a bug"]})
        mock_run.assert_called_once_with(
            ["git", "log", "-n2", "--pretty=%B%x00"],
            capture_output=True, text=True, check=True, encoding="utf-8"
        )

    @patch("subprocess.run")
    def test_collect_empty_history(self, mock_run):
        # Arrange
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=128, cmd="git log", stderr="does not have any commits"
        )
        collector = HistoryCollector(n=5)

        # Act
        result = collector.collect()

        # Assert
        self.assertEqual(result, {"history": []})

    def test_init_invalid_n(self):
        # Act & Assert
        with self.assertRaises(ValueError):
            HistoryCollector(n=0)
        with self.assertRaises(ValueError):
            HistoryCollector(n=-1)


if __name__ == "__main__":
    unittest.main()
