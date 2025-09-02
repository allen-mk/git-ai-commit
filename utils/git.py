import subprocess
from utils.errors import AICommitException


def is_git_repository() -> bool:
    """Checks if the current directory is a Git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() == "true"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def has_staged_changes() -> bool:
    """Checks if there are any staged changes."""
    try:
        # --quiet exits with 1 if there are changes, 0 otherwise.
        # --cached checks the staging area.
        subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            check=True,
        )
        return False  # Exit code 0 means no staged changes
    except FileNotFoundError:
         raise AICommitException("Git is not installed or not in PATH.")
    except subprocess.CalledProcessError:
        return True  # Exit code 1 means there are staged changes
    except Exception as e:
        raise AICommitException(f"An unexpected error occurred while checking for staged changes: {e}")


def get_current_branch_name() -> str:
    """
    Gets the current Git branch name.

    Returns:
        The current branch name.

    Raises:
        AICommitException: If the git command fails or not in a git repository.
    """
    if not is_git_repository():
        raise AICommitException("Not a Git repository.")

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
        return result.stdout.strip()
    except FileNotFoundError:
        raise AICommitException("Git is not installed or not in PATH.")
    except subprocess.CalledProcessError as e:
        raise AICommitException(f"Failed to get current branch name: {e.stderr}")
    except Exception as e:
        raise AICommitException(f"An unexpected error occurred while getting branch name: {e}")


def get_staged_diff() -> str:
    """
    Retrieves the staged changes (diff) from the Git repository.

    Returns:
        The git diff output as a string.

    Raises:
        AICommitException: If the git command fails.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode not in [0, 1]:
             raise AICommitException(f"Failed to get git diff: {result.stderr}")

        return result.stdout
    except FileNotFoundError:
        raise AICommitException("Git is not installed or not in PATH.")
    except Exception as e:
        raise AICommitException(f"An unexpected error occurred while getting git diff: {e}")


def commit(message: str) -> None:
    """
    Creates a Git commit with the given message.

    Args:
        message: The commit message.

    Raises:
        AICommitException: If the git commit command fails.
    """
    try:
        subprocess.run(
            ["git", "commit", "-m", message],
            check=True,
            capture_output=True, # Capture output to check for errors
            text=True,
        )
    except FileNotFoundError:
        raise AICommitException("Git is not installed or not in PATH.")
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip()
        raise AICommitException(f"Failed to create commit: {error_message}")
    except Exception as e:
        raise AICommitException(f"An unexpected error occurred during commit: {e}")
