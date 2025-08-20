"""Utility modules for GovernmentReporter."""

import logging
from typing import Optional

from .citations import build_bluebook_citation
from .config import (get_congress_gov_token, get_court_listener_token,
                     get_federal_register_token, get_google_gemini_api_key)
from .embeddings import GoogleEmbeddingsClient


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance with consistent configuration.
    
    Args:
        name: Logger name. If None, uses the caller's module name.
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or __name__)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


__all__ = [
    "get_court_listener_token",
    "get_federal_register_token",
    "get_congress_gov_token",
    "get_google_gemini_api_key",
    "GoogleEmbeddingsClient",
    "build_bluebook_citation",
    "get_logger",
]
