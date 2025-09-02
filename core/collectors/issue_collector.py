import os
import re
from typing import Any, Mapping, Optional

import httpx

from core.contracts.collector import Collector
from core.registry import collector_registry
from utils.errors import CollectorError
from utils.git import get_current_branch_name, is_git_repository
from utils.logger import logger


@collector_registry.register("issue")
class IssueCollector(Collector):
    """
    Collects issue details from a provider (e.g., GitHub) based on the branch name.
    """

    def __init__(
        self,
        provider: str = "github",
        repo: Optional[str] = None,
        token_env_var: str = "GITHUB_TOKEN",
    ):
        self.provider = provider
        self.repo = repo
        self.token_env_var = token_env_var
        self.client = httpx.Client()

    def _extract_issue_number(self, branch_name: str) -> Optional[str]:
        """Extracts issue number from branch name (e.g., feature/123-foo -> 123)."""
        match = re.search(r"\d+", branch_name)
        return match.group(0) if match else None

    def _get_github_issue(self, issue_number: str) -> Mapping[str, Any]:
        """Fetches issue details from GitHub API."""
        if not self.repo:
            raise CollectorError("GitHub repository (`repo`) not specified in config.")

        token = os.getenv(self.token_env_var)
        headers = {}
        if token:
            headers["Authorization"] = f"token {token}"
        else:
            logger.warning(
                f"Environment variable '{self.token_env_var}' not set. "
                "Making unauthenticated request to GitHub API."
            )

        url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}"
        try:
            response = self.client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise CollectorError(f"Failed to request GitHub API: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Issue {issue_number} not found in repo {self.repo}.")
                return {}
            raise CollectorError(
                f"GitHub API returned error: {e.response.status_code} "
                f"{e.response.text}"
            ) from e

    def collect(self) -> Mapping[str, Any]:
        """
        Collects issue information based on the current git branch name.

        Returns:
            A mapping containing the issue details, or an empty dict if not found.
        """
        if not is_git_repository():
            logger.debug("Not a git repository, skipping issue collection.")
            return {}

        try:
            branch_name = get_current_branch_name()
            issue_number = self._extract_issue_number(branch_name)

            if not issue_number:
                logger.info("No issue number found in branch name, skipping.")
                return {}

            logger.info(f"Found issue number {issue_number} in branch {branch_name}.")

            if self.provider == "github":
                issue_data = self._get_github_issue(issue_number)
                return {"issue": issue_data} if issue_data else {}
            else:
                logger.warning(f"Provider '{self.provider}' is not supported yet.")
                return {}

        except Exception as e:
            raise CollectorError(f"Failed to collect issue details: {e}") from e
