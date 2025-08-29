"""Utility modules for GovernmentReporter.

This package contains shared utilities and helper functions that support the core
functionality of the GovernmentReporter MCP server. The utilities are organized
into specialized modules for different concerns:

- config.py: Environment variable management for API keys and tokens
- citations.py: Legal citation formatting utilities
- monitoring.py: Performance monitoring and progress tracking utilities
- __init__.py: Centralized imports and common utilities like logging

Integration Points:
    - The config module provides secure access to API credentials for all
      external services (Court Listener, Federal Register, Congress.gov, OpenAI)
    - The citations module formats legal references according to Bluebook standards
    - The monitoring module tracks processing performance for bulk operations
    - The logger utility ensures consistent log formatting across all modules

Python Learning Notes:
    - This __init__.py file serves as a package initializer and public API
    - The __all__ list at the bottom controls what gets imported with "from utils import *"
    - Type hints (Optional[str], logging.Logger) help with code clarity and IDE support
    - The logging configuration follows Python's standard logging module patterns
"""

import logging
import logging.config
import os
from pathlib import Path
from typing import Optional

import yaml

from .citations import build_bluebook_citation
from .config import get_court_listener_token, get_openai_api_key
from .monitoring import PerformanceMonitor

# Global flag to track if logging has been configured
_logging_configured = False


def setup_logging(config_path: Optional[Path] = None) -> None:
    """Set up logging configuration from YAML file.

    This function configures the entire logging system using a YAML configuration
    file. It should be called once at application startup, typically in main.py
    or server.py before any other modules request loggers.

    The logging configuration includes:
    - Multiple handlers for different log levels and destinations
    - Rotating file handlers to prevent log files from growing too large
    - Separate handlers for console output (stdout/stderr)
    - Module-specific logging levels and formatting

    Integration with GovernmentReporter:
        This centralized logging setup ensures:
        - Consistent log formatting across all modules
        - Proper log rotation to manage disk usage
        - Separate error and debug log files for easier troubleshooting
        - Production-ready logging with audit trails

    Python Learning Notes:
        - logging.config.dictConfig() applies a complete logging configuration
        - YAML files provide a clean way to define complex logging setups
        - Global configuration means all subsequent getLogger() calls use this setup
        - The logs directory is created automatically if it doesn't exist

    Args:
        config_path (Optional[Path]): Path to the logging configuration YAML file.
            If None, defaults to 'logging_config.yaml' in the project root.

    Raises:
        FileNotFoundError: If the logging configuration file is not found.
        yaml.YAMLError: If the YAML configuration file is malformed.

    Example Usage:
        ```python
        # In main.py or server.py
        from governmentreporter.utils import setup_logging

        setup_logging()  # Uses default config
        # Now all modules can use: logger = logging.getLogger(__name__)
        ```
    """
    global _logging_configured

    if _logging_configured:
        return

    if config_path is None:
        # Default to logging_config.yaml in project root
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "logging_config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Logging config file not found: {config_path}")

    # Ensure logs directory exists
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)

    # Load and apply YAML configuration
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logging.config.dictConfig(config)
    _logging_configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance using the centralized logging configuration.

    This function returns a logger that uses the configuration set up by
    setup_logging(). If setup_logging() hasn't been called yet, it will
    be called automatically with default settings.

    The logger will automatically use the appropriate handlers, formatters,
    and log levels based on the module name and the YAML configuration.

    Integration with GovernmentReporter:
        Different modules get different logging configurations:
        - API modules: DEBUG level with detailed logging
        - Database modules: INFO level with standard logging
        - Processors: DEBUG level for complex operation tracking
        - Utils: INFO level for general purpose logging

    Python Learning Notes:
        - logging.getLogger() with YAML config automatically applies the right setup
        - Module names (like 'governmentreporter.apis.federal_register') are matched
          against logger patterns in the YAML config
        - No manual handler setup needed - everything comes from the config file

    Args:
        name (Optional[str]): Logger name to use. If None, defaults to the utils
            module's __name__. For module-specific logging, pass __name__ explicitly.

    Returns:
        logging.Logger: A configured logger instance ready for use with handlers,
            formatters, and log levels set according to the YAML configuration.

    Example Usage:
        ```python
        # In any module
        from governmentreporter.utils import get_logger

        logger = get_logger(__name__)
        logger.debug("Detailed debug information")  # May or may not show
        logger.info("General information")          # Usually shows
        logger.error("Error occurred")              # Always shows
        ```
    """
    # Ensure logging is configured before returning any logger
    if not _logging_configured:
        setup_logging()

    return logging.getLogger(name or __name__)


__all__ = [
    "get_court_listener_token",
    "get_openai_api_key",
    "build_bluebook_citation",
    "PerformanceMonitor",
    "setup_logging",
    "get_logger",
]
