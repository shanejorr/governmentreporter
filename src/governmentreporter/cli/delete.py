"""
Delete command for removing Qdrant collections.

This module provides CLI commands for safely deleting Qdrant collections,
either individually or all at once. It includes confirmation prompts to
prevent accidental data loss.

Commands:
    governmentreporter delete --all          Delete all collections
    governmentreporter delete --scotus       Delete SCOTUS collection only
    governmentreporter delete --eo           Delete Executive Orders collection only
    governmentreporter delete --collection NAME  Delete specific collection by name

Python Learning Notes:
    - Click provides user-friendly CLI interfaces with automatic help text
    - Confirmation prompts prevent accidental destructive operations
    - Environment variables control database connection settings
"""

import logging
import os
from pathlib import Path
from typing import Optional

import click

from governmentreporter.database import QdrantDBClient

logger = logging.getLogger(__name__)

# Progress database file mapping
PROGRESS_DB_MAPPING = {
    "supreme_court_opinions": "scotus_ingestion.db",
    "executive_orders": "executive_orders_ingestion.db",
}


def delete_progress_database(collection_name: str) -> bool:
    """
    Delete the ingestion progress database for a collection.

    Ingestion progress is tracked in SQLite databases in ./data/progress/.
    When deleting a collection, you should also delete its progress database
    to start fresh on re-ingestion.

    Args:
        collection_name: Name of the Qdrant collection.

    Returns:
        True if progress database was deleted or didn't exist, False on error.

    Python Learning Notes:
        - Path.unlink() deletes a file
        - missing_ok=True prevents errors if file doesn't exist
        - try/except handles unexpected errors gracefully
    """
    # Check if this collection has a progress database
    progress_db_name = PROGRESS_DB_MAPPING.get(collection_name)
    if not progress_db_name:
        # No progress database for this collection
        return True

    progress_db_path = Path("./data/progress") / progress_db_name

    try:
        if progress_db_path.exists():
            progress_db_path.unlink()
            logger.info(f"Deleted progress database: {progress_db_path}")
            return True
        else:
            logger.debug(f"Progress database not found: {progress_db_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to delete progress database {progress_db_path}: {e}")
        return False


def get_qdrant_client(
    db_path: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> QdrantDBClient:
    """
    Initialize and return a Qdrant client.

    Prefers local file-based Qdrant by default. Only uses network connection
    if host is explicitly provided via parameters.

    Args:
        db_path: Path to local Qdrant database (default: ./data/qdrant/qdrant_db)
        host: Qdrant host for remote connection (optional)
        port: Qdrant port for remote connection (default: 6333)

    Returns:
        QdrantDBClient: Configured Qdrant client instance.

    Python Learning Notes:
        - Defaults to local file-based storage for simplicity
        - Remote connection only used when explicitly requested
        - This matches the pattern used by other CLI commands
    """
    # Use remote connection if host is explicitly provided
    if host:
        return QdrantDBClient(host=host, port=port or 6333)

    # Otherwise, default to local file-based
    return QdrantDBClient(db_path=db_path or "./data/qdrant/qdrant_db")


@click.command(name="delete")
@click.option(
    "--all",
    "delete_all",
    is_flag=True,
    help="Delete all collections (requires confirmation)",
)
@click.option(
    "--scotus",
    is_flag=True,
    help="Delete the Supreme Court opinions collection",
)
@click.option(
    "--eo",
    is_flag=True,
    help="Delete the Executive Orders collection",
)
@click.option(
    "--collection",
    type=str,
    help="Delete a specific collection by name",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt (use with caution!)",
)
@click.option(
    "--qdrant-path",
    default="./data/qdrant/qdrant_db",
    help="Path to Qdrant database (default: ./data/qdrant/qdrant_db)",
)
@click.option(
    "--qdrant-host",
    default=None,
    help="Qdrant host for remote connection (e.g., localhost)",
)
@click.option(
    "--qdrant-port",
    type=int,
    default=None,
    help="Qdrant port for remote connection (default: 6333)",
)
def delete_command(
    delete_all: bool,
    scotus: bool,
    eo: bool,
    collection: Optional[str],
    yes: bool,
    qdrant_path: str,
    qdrant_host: Optional[str],
    qdrant_port: Optional[int],
) -> None:
    """
    Delete Qdrant collections.

    This command safely deletes one or more Qdrant collections. By default,
    it will prompt for confirmation before deleting to prevent accidental
    data loss.

    Examples:
        # Delete all collections (with confirmation)
        governmentreporter delete --all

        # Delete SCOTUS collection only
        governmentreporter delete --scotus

        # Delete Executive Orders collection
        governmentreporter delete --eo

        # Delete both SCOTUS and EO
        governmentreporter delete --scotus --eo

        # Delete specific collection by name
        governmentreporter delete --collection supreme_court_opinions

        # Skip confirmation (dangerous!)
        governmentreporter delete --all -y

    Python Learning Notes:
        - Click options create command-line flags automatically
        - is_flag=True creates boolean flags (no value needed)
        - Multiple options can be combined for flexibility
        - Confirmation prompts prevent accidental destructive operations
    """
    # Validate that at least one option was provided
    if not any([delete_all, scotus, eo, collection]):
        click.echo(
            "Error: You must specify what to delete. Use --help for options.",
            err=True,
        )
        raise click.Abort()

    # Initialize Qdrant client
    try:
        client = get_qdrant_client(
            db_path=qdrant_path, host=qdrant_host, port=qdrant_port
        )

        # Show connection info
        if qdrant_host:
            click.echo(f"Connected to Qdrant at {qdrant_host}:{qdrant_port or 6333}\n")
        else:
            click.echo(f"Connected to local Qdrant at {qdrant_path}\n")

    except Exception as e:
        click.echo(f"Error: Failed to connect to Qdrant: {e}", err=True)
        raise click.Abort()

    # Collection name mapping
    COLLECTION_NAMES = {
        "scotus": "supreme_court_opinions",
        "eo": "executive_orders",
    }

    # Determine which collections to delete
    collections_to_delete = []

    if delete_all:
        # Get all existing collections
        try:
            all_collections = client.list_collections()
            if not all_collections:
                click.echo("No collections found in the database.")
                return
            collections_to_delete = all_collections
        except Exception as e:
            click.echo(f"Error: Failed to list collections: {e}", err=True)
            raise click.Abort()
    else:
        # Add specific collections
        if scotus:
            collections_to_delete.append(COLLECTION_NAMES["scotus"])
        if eo:
            collections_to_delete.append(COLLECTION_NAMES["eo"])
        if collection:
            collections_to_delete.append(collection)

    # Display what will be deleted
    click.echo("\nThe following collections will be deleted:")
    for coll in collections_to_delete:
        # Get collection info if available
        info = client.get_collection_info(coll)
        if info:
            click.echo(
                f"  • {coll} ({info['points_count']} documents, "
                f"{info['vectors_count']} vectors)"
            )
        else:
            click.echo(f"  • {coll} (not found - will skip)")

        # Check if there's a progress database for this collection
        if coll in PROGRESS_DB_MAPPING:
            progress_db_path = Path("./data/progress") / PROGRESS_DB_MAPPING[coll]
            if progress_db_path.exists():
                click.echo(f"    └─ Progress database: {PROGRESS_DB_MAPPING[coll]}")

    click.echo("\n⚠️  WARNING: This action cannot be undone!")
    click.echo(
        "This will delete both the Qdrant collection and any associated progress tracking databases."
    )

    # Confirmation prompt (unless --yes flag is used)
    if not yes:
        if not click.confirm("\nAre you sure you want to delete these collections?"):
            click.echo("Deletion cancelled.")
            return

    # Perform deletions
    click.echo("\nDeleting collections and progress databases...")
    deleted_count = 0
    skipped_count = 0

    for coll in collections_to_delete:
        try:
            # Check if collection exists first
            if client.get_collection_info(coll):
                success = client.delete_collection(coll)
                if success:
                    click.echo(f"  ✓ Deleted collection: {coll}")
                    deleted_count += 1

                    # Also delete progress database if it exists
                    if coll in PROGRESS_DB_MAPPING:
                        progress_db_path = (
                            Path("./data/progress") / PROGRESS_DB_MAPPING[coll]
                        )
                        if progress_db_path.exists():
                            delete_progress_database(coll)
                            click.echo(
                                f"    └─ Deleted progress database: {PROGRESS_DB_MAPPING[coll]}"
                            )
                else:
                    click.echo(f"  ✗ Failed to delete {coll}", err=True)
            else:
                click.echo(f"  - Skipped {coll} (does not exist)")
                skipped_count += 1
        except Exception as e:
            click.echo(f"  ✗ Error deleting {coll}: {e}", err=True)

    # Summary
    click.echo(f"\n✓ Deleted {deleted_count} collection(s)")
    if skipped_count > 0:
        click.echo(f"  Skipped {skipped_count} collection(s) (did not exist)")

    # Suggest next steps
    if deleted_count > 0:
        click.echo("\nYou can now re-ingest data using:")
        if "supreme_court_opinions" in collections_to_delete:
            click.echo(
                "  governmentreporter ingest scotus --start-date YYYY-MM-DD --end-date YYYY-MM-DD"
            )
        if "executive_orders" in collections_to_delete:
            click.echo(
                "  governmentreporter ingest eo --start-date YYYY-MM-DD --end-date YYYY-MM-DD"
            )
