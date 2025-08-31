import os
import re
import yaml
from typing import Any, Dict, IO

from utils.errors import ConfigError

# Regex for environment variable substitution
ENV_VAR_MATCHER = re.compile(r"\$\{(\w+)\}")

def _env_var_constructor(loader: yaml.SafeLoader, node: yaml.ScalarNode) -> str:
    """
    Custom YAML constructor to substitute environment variables.
    e.g., ${VAR_NAME} will be replaced by the value of the VAR_NAME environment variable.
    """
    value = loader.construct_scalar(node)
    match = ENV_VAR_MATCHER.match(value)
    if not match:
        return value

    env_var = match.group(1)
    replacement = os.getenv(env_var)
    if replacement is None:
        raise ConfigError(f"Environment variable '{env_var}' not found for substitution in config.")

    return replacement

def get_config_loader() -> yaml.Loader:
    """
    Get a YAML loader that supports environment variable substitution.
    """
    loader = yaml.SafeLoader
    loader.add_constructor("!env", _env_var_constructor)
    loader.add_implicit_resolver("!env", ENV_VAR_MATCHER, None)
    return loader

def load_config(config_file: IO[str]) -> Dict[str, Any]:
    """
    Loads a YAML configuration file.

    Args:
        config_file: A file-like object representing the YAML configuration.

    Returns:
        A dictionary containing the configuration.

    Raises:
        ConfigError: If the file cannot be parsed.
    """
    try:
        loader = get_config_loader()
        config = yaml.load(config_file, Loader=loader)
        return config if config else {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML configuration: {e}") from e
