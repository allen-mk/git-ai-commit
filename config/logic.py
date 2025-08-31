import collections.abc
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.loader import load_config
from config.models import Config
from utils.errors import AICommitException
from utils.logger import logger

DEFAULT_CONFIG_PATH = Path(__file__).parent / "default.yaml"
USER_CONFIG_DIR = Path.home() / ".aicommit"
USER_CONFIG_PATH = USER_CONFIG_DIR / "config.yaml"
PROJECT_CONFIG_FILENAME = ".aicommit.yaml"


def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merges two dictionaries.
    Arrays are replaced, not merged.
    """
    for key, value in source.items():
        if isinstance(value, collections.abc.Mapping) and key in target and isinstance(target[key], collections.abc.Mapping):
            target[key] = deep_merge(target[key], value)
        else:
            target[key] = value
    return target


def find_project_root(start_dir: Path = Path(".")) -> Optional[Path]:
    """
    Finds the project root by searching upwards for a .git directory or pyproject.toml.
    """
    d = start_dir.resolve()
    while d != d.parent:
        if (d / ".git").is_dir() or (d / "pyproject.toml").is_file():
            return d
        d = d.parent
    return None


def find_project_config() -> Optional[Path]:
    """
    Finds the project-specific configuration file (.aicommit.yaml) in the project root.
    """
    project_root = find_project_root()
    if project_root:
        project_config_path = project_root / PROJECT_CONFIG_FILENAME
        if project_config_path.is_file():
            return project_config_path
    return None


def load_and_merge_configs(custom_config_path: Optional[str] = None) -> Config:
    """
    Loads all configurations (default, user, project) and merges them.
    A custom config path can be provided to override all others.
    """
    config_paths: List[Path] = []

    # 1. Default config
    if DEFAULT_CONFIG_PATH.is_file():
        config_paths.append(DEFAULT_CONFIG_PATH)
    else:
        raise AICommitException("Default configuration file not found.")

    # 2. User config
    if USER_CONFIG_PATH.is_file():
        config_paths.append(USER_CONFIG_PATH)

    # 3. Project config
    project_config_path = find_project_config()
    if project_config_path:
        config_paths.append(project_config_path)

    # If a custom config path is provided via CLI, it has the highest precedence.
    if custom_config_path:
        path = Path(custom_config_path)
        if not path.is_file():
            raise AICommitException(f"Custom config file not found at: {custom_config_path}")
        config_paths = [path] # It overrides all others
        logger.info(f"Using custom configuration from: {custom_config_path}")

    merged_config: Dict[str, Any] = {}
    for path in config_paths:
        logger.info(f"Loading configuration from: {path}")
        try:
            with open(path, "r") as f:
                config_data = load_config(f)
                merged_config = deep_merge(merged_config, config_data)
        except Exception as e:
            logger.warning(f"Could not load or parse config at {path}: {e}")

    try:
        final_config = Config(**merged_config)
        logger.debug(f"Final merged config: {final_config.model_dump_json(indent=2)}")
        return final_config
    except Exception as e:
        raise AICommitException(f"Configuration validation failed: {e}")
