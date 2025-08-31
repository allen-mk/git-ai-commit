"""
Defines custom exception classes for the application.
"""

class AICommitException(Exception):
    """Base exception class for aicommit application."""
    pass

class CollectorError(AICommitException):
    """Raised when an error occurs during context collection."""
    pass

class ProviderError(AICommitException):
    """Raised when an error occurs with an LLM provider."""
    pass

class FormatterError(AICommitException):
    """Raised when an error occurs during message formatting."""
    pass

class ConfigError(AICommitException):
    """Raised when there is a configuration error."""
    pass
