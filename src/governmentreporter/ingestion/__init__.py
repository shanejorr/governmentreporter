"""
Document ingestion module for GovernmentReporter.

This module provides batch ingestion capabilities for government documents:
- Supreme Court opinions from CourtListener
- Executive Orders from Federal Register
- Progress tracking with SQLite
- Batch processing with error recovery
- Performance monitoring

Classes:
    DocumentIngester: Abstract base class for all ingesters
    SCOTUSIngester: Supreme Court opinion ingester
    ExecutiveOrderIngester: Executive Order ingester
    ProgressTracker: SQLite-based progress tracking
"""

from .base import DocumentIngester
from .scotus import SCOTUSIngester
from .executive_orders import ExecutiveOrderIngester
from .progress import ProgressTracker

__all__ = [
    "DocumentIngester",
    "SCOTUSIngester",
    "ExecutiveOrderIngester",
    "ProgressTracker",
]