"""
Progress tracking system for document ingestion using SQLite.

This module provides a lightweight, persistent progress tracking system
for batch document ingestion. It enables resumable operations and provides
detailed statistics about processing status.

The tracker uses SQLite to maintain state across script runs, allowing
for safe interruption and resumption of large batch jobs.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """
    Enumeration of document processing states.

    A document moves through these states during ingestion:
    - PENDING: Document identified but not yet processed
    - PROCESSING: Currently being worked on
    - COMPLETED: Successfully ingested into Qdrant
    - FAILED: Error occurred during processing
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressTracker:
    """
    SQLite-based progress tracker for document ingestion.

    This class manages a SQLite database that tracks the processing status
    of documents during batch ingestion. It provides methods to:
    - Track which documents have been processed
    - Resume interrupted batch jobs
    - Generate statistics about processing progress
    - Store error information for failed documents

    Attributes:
        db_path (Path): Path to the SQLite database file
        conn (sqlite3.Connection): Database connection
        document_type (str): Type of documents being tracked (e.g., 'scotus', 'executive_order')
    """

    def __init__(
        self, db_path: str = "ingestion_progress.db", document_type: str = "generic"
    ):
        """
        Initialize the progress tracker with a SQLite database.

        Args:
            db_path: Path to the SQLite database file. Will be created if it doesn't exist.
            document_type: Type of documents being tracked (for organizing multiple ingestion types).
        """
        self.db_path = Path(db_path)
        self.document_type = document_type
        self.conn = sqlite3.connect(
            self.db_path, isolation_level=None
        )  # Autocommit mode
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self._initialize_database()

    def _initialize_database(self) -> None:
        """
        Create the database tables if they don't exist.

        The main table stores:
        - document_id: Unique identifier from the source API
        - document_type: Type of document (scotus, executive_order, etc.)
        - status: Current processing status
        - error_message: Error details if processing failed
        - metadata: JSON field for storing additional document info
        - created_at: When the record was first created
        - updated_at: Last status update time
        - processing_time_ms: Time taken to process (for performance metrics)
        """
        cursor = self.conn.cursor()

        # Main tracking table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS document_progress (
                document_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processing_time_ms INTEGER,
                PRIMARY KEY (document_id, document_type)
            )
        """
        )

        # Index for efficient status queries
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_status_type 
            ON document_progress(document_type, status)
        """
        )

        # Statistics table for tracking overall progress
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ingestion_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_type TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                total_documents INTEGER DEFAULT 0,
                completed_documents INTEGER DEFAULT 0,
                failed_documents INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                parameters TEXT
            )
        """
        )

    def start_run(
        self, start_date: str, end_date: str, parameters: Dict[str, Any] = None
    ) -> int:
        """
        Start a new ingestion run and return its ID.

        Args:
            start_date: Start date for the document range
            end_date: End date for the document range
            parameters: Additional parameters for this run

        Returns:
            run_id: Unique identifier for this ingestion run
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO ingestion_runs (document_type, start_date, end_date, parameters)
            VALUES (?, ?, ?, ?)
        """,
            (self.document_type, start_date, end_date, json.dumps(parameters or {})),
        )

        return cursor.lastrowid

    def end_run(self, run_id: int) -> None:
        """
        Mark an ingestion run as completed.

        Args:
            run_id: The ID of the run to complete
        """
        cursor = self.conn.cursor()

        # Update run statistics
        cursor.execute(
            """
            UPDATE ingestion_runs 
            SET completed_at = CURRENT_TIMESTAMP,
                total_documents = (
                    SELECT COUNT(*) FROM document_progress 
                    WHERE document_type = ?
                ),
                completed_documents = (
                    SELECT COUNT(*) FROM document_progress 
                    WHERE document_type = ? AND status = 'completed'
                ),
                failed_documents = (
                    SELECT COUNT(*) FROM document_progress 
                    WHERE document_type = ? AND status = 'failed'
                )
            WHERE run_id = ?
        """,
            (self.document_type, self.document_type, self.document_type, run_id),
        )

    def add_document(self, document_id: str, metadata: Dict[str, Any] = None) -> None:
        """
        Add a new document to track.

        Args:
            document_id: Unique identifier for the document
            metadata: Optional metadata about the document
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO document_progress (document_id, document_type, status, metadata)
                VALUES (?, ?, 'pending', ?)
            """,
                (document_id, self.document_type, json.dumps(metadata or {})),
            )
        except sqlite3.IntegrityError:
            # Document already exists, ignore
            pass

    def is_processed(self, document_id: str) -> bool:
        """
        Check if a document has already been successfully processed.

        Args:
            document_id: Document identifier to check

        Returns:
            True if the document was successfully processed, False otherwise
        """
        cursor = self.conn.cursor()
        result = cursor.execute(
            """
            SELECT status FROM document_progress 
            WHERE document_id = ? AND document_type = ? AND status = 'completed'
        """,
            (document_id, self.document_type),
        ).fetchone()

        return result is not None

    def mark_processing(self, document_id: str) -> None:
        """
        Mark a document as currently being processed.

        Args:
            document_id: Document to mark as processing
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE document_progress 
            SET status = 'processing', updated_at = CURRENT_TIMESTAMP
            WHERE document_id = ? AND document_type = ?
        """,
            (document_id, self.document_type),
        )

    def mark_completed(
        self, document_id: str, processing_time_ms: Optional[int] = None
    ) -> None:
        """
        Mark a document as successfully completed.

        Args:
            document_id: Document that was successfully processed
            processing_time_ms: Optional processing time in milliseconds
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE document_progress 
            SET status = 'completed', 
                updated_at = CURRENT_TIMESTAMP,
                processing_time_ms = ?,
                error_message = NULL
            WHERE document_id = ? AND document_type = ?
        """,
            (processing_time_ms, document_id, self.document_type),
        )

    def mark_failed(self, document_id: str, error_message: str) -> None:
        """
        Mark a document as failed with an error message.

        Args:
            document_id: Document that failed to process
            error_message: Description of what went wrong
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE document_progress 
            SET status = 'failed', 
                error_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE document_id = ? AND document_type = ?
        """,
            (error_message, document_id, self.document_type),
        )

    def get_pending_documents(self, limit: Optional[int] = None) -> List[str]:
        """
        Get list of documents that still need to be processed.

        Args:
            limit: Maximum number of pending documents to return

        Returns:
            List of document IDs that are pending processing
        """
        cursor = self.conn.cursor()
        query = """
            SELECT document_id FROM document_progress 
            WHERE document_type = ? AND status IN ('pending', 'failed')
            ORDER BY created_at
        """

        if limit:
            query += f" LIMIT {limit}"

        results = cursor.execute(query, (self.document_type,)).fetchall()
        return [row["document_id"] for row in results]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get detailed statistics about the ingestion progress.

        Returns:
            Dictionary containing:
            - total: Total number of documents
            - completed: Successfully processed documents
            - failed: Documents that failed processing
            - pending: Documents waiting to be processed
            - processing: Documents currently being processed
            - success_rate: Percentage of successful processing
            - avg_processing_time_ms: Average time to process a document
            - failed_documents: List of failed document IDs with error messages
        """
        cursor = self.conn.cursor()

        # Get counts by status
        stats = {
            "document_type": self.document_type,
            "total": 0,
            "completed": 0,
            "failed": 0,
            "pending": 0,
            "processing": 0,
            "success_rate": 0.0,
            "avg_processing_time_ms": None,
            "failed_documents": [],
        }

        # Count by status
        status_counts = cursor.execute(
            """
            SELECT status, COUNT(*) as count 
            FROM document_progress 
            WHERE document_type = ?
            GROUP BY status
        """,
            (self.document_type,),
        ).fetchall()

        for row in status_counts:
            status = row["status"]
            count = row["count"]
            if status == "completed":
                stats["completed"] = count
            elif status == "failed":
                stats["failed"] = count
            elif status == "pending":
                stats["pending"] = count
            elif status == "processing":
                stats["processing"] = count
            stats["total"] += count

        # Calculate success rate
        if stats["completed"] + stats["failed"] > 0:
            stats["success_rate"] = (
                stats["completed"] / (stats["completed"] + stats["failed"]) * 100
            )

        # Get average processing time
        avg_time = cursor.execute(
            """
            SELECT AVG(processing_time_ms) as avg_time
            FROM document_progress 
            WHERE document_type = ? AND status = 'completed' AND processing_time_ms IS NOT NULL
        """,
            (self.document_type,),
        ).fetchone()

        if avg_time and avg_time["avg_time"]:
            stats["avg_processing_time_ms"] = int(avg_time["avg_time"])

        # Get failed documents with error messages
        failed = cursor.execute(
            """
            SELECT document_id, error_message, updated_at
            FROM document_progress 
            WHERE document_type = ? AND status = 'failed'
            ORDER BY updated_at DESC
            LIMIT 10
        """,
            (self.document_type,),
        ).fetchall()

        stats["failed_documents"] = [
            {
                "document_id": row["document_id"],
                "error": row["error_message"],
                "failed_at": row["updated_at"],
            }
            for row in failed
        ]

        return stats

    def reset_processing_status(self) -> None:
        """
        Reset any documents stuck in 'processing' state back to 'pending'.

        This is useful when restarting after a crash where documents may
        have been left in the processing state.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE document_progress 
            SET status = 'pending', updated_at = CURRENT_TIMESTAMP
            WHERE document_type = ? AND status = 'processing'
        """,
            (self.document_type,),
        )

        count = cursor.rowcount
        if count > 0:
            logger.info(f"Reset {count} documents from 'processing' to 'pending' state")

    def get_run_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get history of recent ingestion runs.

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of run information dictionaries
        """
        cursor = self.conn.cursor()
        runs = cursor.execute(
            """
            SELECT * FROM ingestion_runs 
            WHERE document_type = ?
            ORDER BY started_at DESC
            LIMIT ?
        """,
            (self.document_type, limit),
        ).fetchall()

        return [dict(row) for row in runs]

    def close(self) -> None:
        """
        Close the database connection.
        """
        if self.conn:
            self.conn.close()
