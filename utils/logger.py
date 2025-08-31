import sys
import loguru

def setup_logger(log_level="INFO", log_file="aicommit.log"):
    """
    Set up a logger with console and file handlers.

    Args:
        log_level (str): The minimum level of logs to display.
        log_file (str): The file to which logs should be written.
    """
    loguru.logger.remove()  # Remove default handler

    # Console logger
    loguru.logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # File logger
    loguru.logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    return loguru.logger

# Initialize a default logger instance
logger = setup_logger()
