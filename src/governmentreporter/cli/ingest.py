"""
Document ingestion CLI commands.

Provides commands for ingesting Supreme Court opinions and Executive Orders
into the Qdrant vector database.
"""

import sys
from datetime import datetime

import click


@click.group()
def ingest():
    """
    Ingest government documents into vector database.

    Commands:
        scotus    - Ingest Supreme Court opinions
        eo        - Ingest Executive Orders
    """
    pass


@ingest.command()
@click.option(
    "--start-date",
    required=True,
    help="Start date for opinion range (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    required=True,
    help="End date for opinion range (YYYY-MM-DD)",
)
@click.option(
    "--batch-size",
    type=int,
    default=50,
    help="Number of opinions to process in each batch (default: 50)",
)
@click.option(
    "--progress-db",
    default="./data/progress/scotus_ingestion.db",
    help="Path to SQLite progress database (default: ./data/progress/scotus_ingestion.db)",
)
@click.option(
    "--qdrant-db-path",
    default="./data/qdrant/qdrant_db",
    help="Path to Qdrant database directory (default: ./data/qdrant/qdrant_db)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run without actually storing documents in Qdrant",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging",
)
def scotus(
    start_date, end_date, batch_size, progress_db, qdrant_db_path, dry_run, verbose
):
    """
    Ingest Supreme Court opinions from CourtListener API.

    Fetches opinions within the specified date range, processes them through
    the document chunking and metadata extraction pipeline, generates embeddings,
    and stores them in Qdrant for semantic search.

    Example:
        governmentreporter ingest scotus --start-date 2020-01-01 --end-date 2024-12-31
        governmentreporter ingest scotus --start-date 2020-01-01 --end-date 2024-12-31 --dry-run
    """
    # Validate dates
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        click.echo("Error: Dates must be in YYYY-MM-DD format", err=True)
        sys.exit(1)

    # Import here to avoid loading heavy dependencies unless needed
    from ..ingestion.scotus import SCOTUSIngester
    from ..utils.monitoring import setup_logging

    # Setup logging
    setup_logging(verbose)

    # Run ingestion
    ingester = SCOTUSIngester(
        start_date=start_date,
        end_date=end_date,
        batch_size=batch_size,
        dry_run=dry_run,
        progress_db=progress_db,
        qdrant_db_path=qdrant_db_path,
    )

    try:
        ingester.run()
    except KeyboardInterrupt:
        click.echo("\n\nIngestion interrupted by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@ingest.command()
@click.option(
    "--start-date",
    required=True,
    help="Start date for order range (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    required=True,
    help="End date for order range (YYYY-MM-DD)",
)
@click.option(
    "--batch-size",
    type=int,
    default=25,
    help="Number of orders to process in each batch (default: 25)",
)
@click.option(
    "--progress-db",
    default="./data/progress/executive_orders_ingestion.db",
    help="Path to SQLite progress database (default: ./data/progress/executive_orders_ingestion.db)",
)
@click.option(
    "--qdrant-db-path",
    default="./data/qdrant/qdrant_db",
    help="Path to Qdrant database directory (default: ./data/qdrant/qdrant_db)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run without actually storing documents in Qdrant",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging",
)
def eo(start_date, end_date, batch_size, progress_db, qdrant_db_path, dry_run, verbose):
    """
    Ingest Executive Orders from Federal Register API.

    Fetches Executive Orders within the specified date range, processes them
    through the document chunking and metadata extraction pipeline, generates
    embeddings, and stores them in Qdrant for semantic search.

    Example:
        governmentreporter ingest eo --start-date 2021-01-20 --end-date 2024-12-31
        governmentreporter ingest eo --start-date 2021-01-20 --end-date 2024-12-31 --dry-run
    """
    # Validate dates
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if start > end:
            click.echo("Error: Start date must be before end date", err=True)
            sys.exit(1)
    except ValueError:
        click.echo("Error: Dates must be in YYYY-MM-DD format", err=True)
        sys.exit(1)

    # Import here to avoid loading heavy dependencies unless needed
    from ..ingestion.executive_orders import ExecutiveOrderIngester
    from ..utils.monitoring import setup_logging

    # Setup logging
    setup_logging(verbose)

    # Run ingestion
    ingester = ExecutiveOrderIngester(
        start_date=start_date,
        end_date=end_date,
        batch_size=batch_size,
        dry_run=dry_run,
        progress_db=progress_db,
        qdrant_db_path=qdrant_db_path,
    )

    try:
        ingester.run()
    except KeyboardInterrupt:
        click.echo("\n\nIngestion interrupted by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@ingest.command()
@click.option(
    "--start-date",
    required=True,
    help="Start date for document range (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    required=True,
    help="End date for document range (YYYY-MM-DD)",
)
@click.option(
    "--qdrant-db-path",
    default="./data/qdrant/qdrant_db",
    help="Path to Qdrant database directory (default: ./data/qdrant/qdrant_db)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run without actually storing documents in Qdrant",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging",
)
def all(start_date, end_date, qdrant_db_path, dry_run, verbose):
    """
    Ingest both Supreme Court opinions and Executive Orders sequentially.

    Runs SCOTUS ingestion first, then Executive Order ingestion for the same
    date range. Uses default batch sizes (50 for SCOTUS, 25 for EO). If SCOTUS
    ingestion fails, EO ingestion will not run.

    Example:
        governmentreporter ingest all --start-date 2024-01-01 --end-date 2024-12-31
        governmentreporter ingest all --start-date 2024-01-01 --end-date 2024-12-31 --dry-run
    """
    # Validate dates
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if start > end:
            click.echo("Error: Start date must be before end date", err=True)
            sys.exit(1)
    except ValueError:
        click.echo("Error: Dates must be in YYYY-MM-DD format", err=True)
        sys.exit(1)

    # Import here to avoid loading heavy dependencies unless needed
    from ..ingestion.executive_orders import ExecutiveOrderIngester
    from ..ingestion.scotus import SCOTUSIngester
    from ..utils.monitoring import setup_logging

    # Setup logging
    setup_logging(verbose)

    click.echo("=" * 80)
    click.echo("INGESTING ALL DOCUMENTS")
    click.echo("=" * 80)
    click.echo(f"Date Range: {start_date} to {end_date}")
    click.echo(f"Dry Run: {dry_run}")
    click.echo("=" * 80)

    # 1. Run SCOTUS ingestion
    click.echo("\n[1/2] Running SCOTUS Opinion Ingestion...")
    click.echo("-" * 80)
    try:
        scotus_ingester = SCOTUSIngester(
            start_date=start_date,
            end_date=end_date,
            batch_size=50,  # Default batch size
            dry_run=dry_run,
            progress_db="./data/progress/scotus_ingestion.db",
            qdrant_db_path=qdrant_db_path,
        )
        scotus_ingester.run()
        click.echo("\n✓ SCOTUS ingestion completed successfully")
    except KeyboardInterrupt:
        click.echo("\n\nIngestion interrupted by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\n✗ SCOTUS ingestion failed: {e}", err=True)
        click.echo("Aborting Executive Order ingestion", err=True)
        sys.exit(1)

    # 2. Run Executive Order ingestion
    click.echo("\n[2/2] Running Executive Order Ingestion...")
    click.echo("-" * 80)
    try:
        eo_ingester = ExecutiveOrderIngester(
            start_date=start_date,
            end_date=end_date,
            batch_size=25,  # Default batch size
            dry_run=dry_run,
            progress_db="./data/progress/executive_orders_ingestion.db",
            qdrant_db_path=qdrant_db_path,
        )
        eo_ingester.run()
        click.echo("\n✓ Executive Order ingestion completed successfully")
    except KeyboardInterrupt:
        click.echo("\n\nIngestion interrupted by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\n✗ Executive Order ingestion failed: {e}", err=True)
        sys.exit(1)

    # Final summary
    click.echo("\n" + "=" * 80)
    click.echo("ALL INGESTION COMPLETE")
    click.echo("=" * 80)
    click.echo("✓ SCOTUS opinions ingested successfully")
    click.echo("✓ Executive Orders ingested successfully")
    click.echo("\nUse 'governmentreporter info collections' to view statistics")
    click.echo("=" * 80)
