"""
Database information and statistics CLI commands.

Provides commands for inspecting Qdrant database contents, viewing
collection statistics, and browsing sample documents.
"""

import sys
from datetime import datetime
from typing import Optional

import click


@click.group()
def info():
    """
    View database information and statistics.

    Commands:
        collections - List all collections with statistics
        sample      - Show sample documents from a collection
        stats       - Show detailed statistics for a collection
    """
    pass


@info.command()
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
def collections(
    qdrant_path: Optional[str], qdrant_host: Optional[str], qdrant_port: Optional[int]
):
    """
    List all collections in the database with statistics.

    Shows collection names, document counts, and basic metadata about
    what has been ingested into the vector database.

    Examples:
        governmentreporter info collections
        governmentreporter info collections --qdrant-host localhost --qdrant-port 6333
    """
    from ..database.qdrant import QdrantDBClient

    try:
        # Initialize Qdrant client
        if qdrant_host:
            client = QdrantDBClient(host=qdrant_host, port=qdrant_port or 6333)
            click.echo(f"Connected to Qdrant at {qdrant_host}:{qdrant_port or 6333}\n")
        else:
            client = QdrantDBClient(db_path=qdrant_path)
            click.echo(f"Connected to local Qdrant at {qdrant_path}\n")

        # Get list of collections
        collection_names = client.list_collections()

        if not collection_names:
            click.echo("No collections found in the database.")
            click.echo("\nTo add documents, use:")
            click.echo(
                "  governmentreporter ingest scotus --start-date YYYY-MM-DD --end-date YYYY-MM-DD"
            )
            click.echo(
                "  governmentreporter ingest eo --start-date YYYY-MM-DD --end-date YYYY-MM-DD"
            )
            sys.exit(0)

        click.echo("=" * 80)
        click.echo("QDRANT COLLECTIONS")
        click.echo("=" * 80)

        for collection_name in collection_names:
            try:
                # Get collection info
                info = client.get_collection_info(collection_name)
                if not info:
                    continue

                click.echo(f"\n📚 Collection: {collection_name}")
                click.echo("-" * 80)

                # Handle None values gracefully
                points_count = info.get("points_count")
                vectors_count = info.get("vectors_count")
                indexed_count = info.get("indexed_vectors_count")
                status = info.get("status", "unknown")

                click.echo(
                    f"Documents:        {points_count:,}"
                    if points_count is not None
                    else "Documents:        N/A"
                )

                # vectors_count can be None in newer Qdrant versions
                if vectors_count is not None:
                    click.echo(f"Vectors:          {vectors_count:,}")
                else:
                    # vectors_count is None - show points_count as proxy
                    click.echo(
                        f"Vectors:          {points_count:,} (using points count)"
                        if points_count is not None
                        else "Vectors:          N/A"
                    )

                # indexed_vectors_count shows HNSW index size (0 if using exact search)
                if indexed_count == 0 and points_count is not None and points_count > 0:
                    click.echo(
                        f"Indexed Vectors:  {indexed_count:,} (using exact search)"
                    )
                else:
                    click.echo(
                        f"Indexed Vectors:  {indexed_count:,}"
                        if indexed_count is not None
                        else "Indexed Vectors:  N/A"
                    )

                click.echo(f"Status:           {status}")

                # Get a sample document to extract metadata
                try:
                    sample_results = client.search(
                        query_embedding=[0.0] * 1536,  # Dummy vector for sampling
                        collection_name=collection_name,
                        limit=1,
                    )

                    if sample_results:
                        metadata = sample_results[0].document.metadata

                        # Display collection-specific metadata
                        if collection_name == "supreme_court_opinions":
                            click.echo(f"Type:             Supreme Court Opinions")
                            if "date" in metadata:
                                click.echo(
                                    f"Sample Date:      {metadata.get('date', 'N/A')}"
                                )
                        elif collection_name == "executive_orders":
                            click.echo(f"Type:             Executive Orders")
                            if "signing_date" in metadata:
                                click.echo(
                                    f"Sample Date:      {metadata.get('signing_date', 'N/A')}"
                                )

                except Exception as e:
                    # Sampling failed, skip metadata display
                    pass

            except Exception as e:
                click.echo(f"\n❌ Error reading collection {collection_name}: {e}")

        click.echo("\n" + "=" * 80)
        click.echo(f"Total Collections: {len(collection_names)}")
        click.echo("=" * 80)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@info.command()
@click.argument(
    "collection",
    type=click.Choice(
        ["scotus", "eo", "supreme_court_opinions", "executive_orders"],
        case_sensitive=False,
    ),
)
@click.option(
    "--limit",
    type=int,
    default=5,
    help="Number of sample documents to show (default: 5)",
)
@click.option(
    "--show-text",
    is_flag=True,
    help="Show full chunk text in samples",
)
@click.option(
    "--qdrant-path",
    default="./data/qdrant/qdrant_db",
    help="Path to Qdrant database (default: ./data/qdrant/qdrant_db)",
)
@click.option(
    "--qdrant-host",
    default=None,
    help="Qdrant host for remote connection",
)
@click.option(
    "--qdrant-port",
    type=int,
    default=None,
    help="Qdrant port for remote connection",
)
def sample(
    collection: str,
    limit: int,
    show_text: bool,
    qdrant_path: Optional[str],
    qdrant_host: Optional[str],
    qdrant_port: Optional[int],
):
    """
    Show sample documents from a collection.

    Retrieves a few sample documents to help you understand what's in
    the database and verify ingestion worked correctly.

    Examples:
        governmentreporter info sample scotus
        governmentreporter info sample eo --limit 10 --show-text
    """
    from ..database.qdrant import QdrantDBClient

    # Map friendly names to collection names
    collection_map = {
        "scotus": "supreme_court_opinions",
        "eo": "executive_orders",
        "supreme_court_opinions": "supreme_court_opinions",
        "executive_orders": "executive_orders",
    }
    collection_name = collection_map[collection.lower()]

    try:
        # Initialize Qdrant client
        if qdrant_host:
            client = QdrantDBClient(host=qdrant_host, port=qdrant_port or 6333)
        else:
            client = QdrantDBClient(db_path=qdrant_path)

        click.echo(f"Fetching {limit} sample documents from {collection_name}...\n")

        # Use a dummy query vector to get random samples
        # (Qdrant doesn't have a "get random" method, so we search with a zero vector)
        results = client.search(
            query_embedding=[0.0] * 1536, collection_name=collection_name, limit=limit
        )

        if not results:
            click.echo(f"No documents found in {collection_name}")
            sys.exit(1)

        click.echo("=" * 80)
        click.echo(f"SAMPLE DOCUMENTS FROM {collection_name.upper()}")
        click.echo("=" * 80)

        for i, result in enumerate(results, 1):
            doc = result.document
            # Check if metadata is nested
            metadata = doc.metadata
            if "metadata" in metadata and isinstance(metadata["metadata"], dict):
                # Flatten nested metadata
                nested = metadata.pop("metadata")
                metadata.update(nested)

            click.echo(f"\n[{i}] Document ID: {doc.id}")
            click.echo("-" * 80)

            # Display metadata based on collection type
            if collection_name == "supreme_court_opinions":
                click.echo(
                    f"Case Name:        {metadata.get('case_name', metadata.get('title', 'N/A'))}"
                )
                click.echo(f"Citation:         {metadata.get('citation', 'N/A')}")
                click.echo(
                    f"Date:             {metadata.get('date', metadata.get('publication_date', 'N/A'))}"
                )
                click.echo(f"Opinion Type:     {metadata.get('opinion_type', 'N/A')}")
                if metadata.get("justice"):
                    click.echo(f"Justice:          {metadata['justice']}")
                if metadata.get("section_label"):
                    click.echo(f"Section:          {metadata['section_label']}")
                click.echo(f"Chunk Index:      {metadata.get('chunk_index', 'N/A')}")

            elif collection_name == "executive_orders":
                click.echo(f"Title:            {metadata.get('title', 'N/A')}")
                click.echo(
                    f"EO Number:        {metadata.get('executive_order_number', 'N/A')}"
                )
                click.echo(f"President:        {metadata.get('president', 'N/A')}")
                click.echo(
                    f"Signing Date:     {metadata.get('signing_date', metadata.get('publication_date', 'N/A'))}"
                )
                if metadata.get("section_title"):
                    click.echo(f"Section:          {metadata['section_title']}")
                click.echo(f"Chunk Index:      {metadata.get('chunk_index', 'N/A')}")

            # Show text if requested
            if show_text:
                text_preview = doc.text[:500] if len(doc.text) > 500 else doc.text
                truncated = " [...]" if len(doc.text) > 500 else ""
                click.echo(f"\nText Preview:\n{text_preview}{truncated}")

        click.echo("\n" + "=" * 80)
        click.echo(f"Showing {len(results)} of {len(results)} samples")
        click.echo("=" * 80)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@info.command()
@click.argument(
    "collection",
    type=click.Choice(
        ["scotus", "eo", "supreme_court_opinions", "executive_orders"],
        case_sensitive=False,
    ),
)
@click.option(
    "--qdrant-path",
    default="./data/qdrant/qdrant_db",
    help="Path to Qdrant database (default: ./data/qdrant/qdrant_db)",
)
@click.option(
    "--qdrant-host",
    default=None,
    help="Qdrant host for remote connection",
)
@click.option(
    "--qdrant-port",
    type=int,
    default=None,
    help="Qdrant port for remote connection",
)
def stats(
    collection: str,
    qdrant_path: Optional[str],
    qdrant_host: Optional[str],
    qdrant_port: Optional[int],
):
    """
    Show detailed statistics for a specific collection.

    Analyzes the collection to provide insights about date ranges,
    document types, and other metadata distributions.

    Examples:
        governmentreporter info stats scotus
        governmentreporter info stats eo
    """
    from collections import Counter

    from ..database.qdrant import QdrantDBClient

    # Map friendly names to collection names
    collection_map = {
        "scotus": "supreme_court_opinions",
        "eo": "executive_orders",
        "supreme_court_opinions": "supreme_court_opinions",
        "executive_orders": "executive_orders",
    }
    collection_name = collection_map[collection.lower()]

    try:
        # Initialize Qdrant client
        if qdrant_host:
            client = QdrantDBClient(host=qdrant_host, port=qdrant_port or 6333)
        else:
            client = QdrantDBClient(db_path=qdrant_path)

        click.echo(f"Analyzing {collection_name}...\n")

        # Get basic collection info
        info = client.get_collection_info(collection_name)
        if not info:
            click.echo(f"Collection {collection_name} not found.")
            sys.exit(1)

        # Sample documents to analyze metadata
        sample_size = min(1000, info["points_count"])
        results = client.search(
            query_embedding=[0.0] * 1536,
            collection_name=collection_name,
            limit=sample_size,
        )

        click.echo("=" * 80)
        click.echo(f"STATISTICS FOR {collection_name.upper()}")
        click.echo("=" * 80)

        # Basic stats
        click.echo(f"\n📊 Basic Statistics")
        click.echo("-" * 80)

        # Handle None values gracefully
        points_count = info.get("points_count")
        vectors_count = info.get("vectors_count")
        indexed_count = info.get("indexed_vectors_count")
        status = info.get("status", "unknown")

        click.echo(
            f"Total Documents:     {points_count:,}"
            if points_count is not None
            else "Total Documents:     N/A"
        )

        # vectors_count can be None in newer Qdrant versions
        if vectors_count is not None:
            click.echo(f"Total Vectors:       {vectors_count:,}")
        else:
            # vectors_count is None - show points_count as proxy
            click.echo(
                f"Total Vectors:       {points_count:,} (using points count)"
                if points_count is not None
                else "Total Vectors:       N/A"
            )

        # indexed_vectors_count shows HNSW index size (0 if using exact search)
        if indexed_count == 0 and points_count is not None and points_count > 0:
            click.echo(f"Indexed Vectors:     {indexed_count:,} (using exact search)")
        else:
            click.echo(
                f"Indexed Vectors:     {indexed_count:,}"
                if indexed_count is not None
                else "Indexed Vectors:     N/A"
            )

        click.echo(f"Collection Status:   {status}")
        click.echo(f"Sample Size:         {len(results):,} documents analyzed")

        if not results:
            click.echo("\nNo documents available for detailed analysis.")
            sys.exit(0)

        # Analyze metadata
        if collection_name == "supreme_court_opinions":
            opinion_types = []
            justices = []
            dates = []
            cases = set()

            for result in results:
                metadata = result.document.metadata
                # Flatten nested metadata if present
                if "metadata" in metadata and isinstance(metadata["metadata"], dict):
                    nested = metadata.get("metadata", {})
                    metadata = {**metadata, **nested}
                if "opinion_type" in metadata:
                    opinion_types.append(metadata["opinion_type"])
                if "justice" in metadata:
                    justices.append(metadata["justice"])
                if "date" in metadata:
                    dates.append(metadata["date"])
                if "case_name" in metadata:
                    cases.add(metadata["case_name"])

            # Opinion type distribution
            if opinion_types:
                click.echo(f"\n📝 Opinion Type Distribution")
                click.echo("-" * 80)
                type_counts = Counter(opinion_types)
                for opinion_type, count in type_counts.most_common():
                    percentage = (count / len(opinion_types)) * 100
                    click.echo(f"{opinion_type:20s} {count:5,} ({percentage:5.1f}%)")

            # Top justices
            if justices:
                click.echo(f"\n⚖️  Most Common Justices (Top 10)")
                click.echo("-" * 80)
                justice_counts = Counter(justices)
                for justice, count in justice_counts.most_common(10):
                    click.echo(f"{justice:20s} {count:5,} chunks")

            # Date range
            if dates:
                dates_sorted = sorted(dates)
                click.echo(f"\n📅 Date Range")
                click.echo("-" * 80)
                click.echo(f"Earliest:            {dates_sorted[0]}")
                click.echo(f"Latest:              {dates_sorted[-1]}")

            # Unique cases
            click.echo(f"\n📚 Case Coverage")
            click.echo("-" * 80)
            click.echo(f"Unique Cases:        {len(cases):,} (in sample)")

        elif collection_name == "executive_orders":
            presidents = []
            dates = []
            eo_numbers = set()
            agencies = []

            for result in results:
                metadata = result.document.metadata
                # Flatten nested metadata if present
                if "metadata" in metadata and isinstance(metadata["metadata"], dict):
                    nested = metadata.get("metadata", {})
                    metadata = {**metadata, **nested}
                if "president" in metadata:
                    presidents.append(metadata["president"])
                if "signing_date" in metadata:
                    dates.append(metadata["signing_date"])
                if "executive_order_number" in metadata:
                    eo_numbers.add(metadata["executive_order_number"])
                if "impacted_agencies" in metadata and isinstance(
                    metadata["impacted_agencies"], list
                ):
                    agencies.extend(metadata["impacted_agencies"])

            # President distribution
            if presidents:
                click.echo(f"\n🏛️  President Distribution")
                click.echo("-" * 80)
                president_counts = Counter(presidents)
                for president, count in president_counts.most_common():
                    percentage = (count / len(presidents)) * 100
                    click.echo(
                        f"{president:20s} {count:5,} chunks ({percentage:5.1f}%)"
                    )

            # Date range
            if dates:
                dates_sorted = sorted(dates)
                click.echo(f"\n📅 Date Range")
                click.echo("-" * 80)
                click.echo(f"Earliest:            {dates_sorted[0]}")
                click.echo(f"Latest:              {dates_sorted[-1]}")

            # Unique EOs
            click.echo(f"\n📜 Executive Order Coverage")
            click.echo("-" * 80)
            click.echo(f"Unique Orders:       {len(eo_numbers):,} (in sample)")

            # Top agencies
            if agencies:
                click.echo(f"\n🏢 Most Impacted Agencies (Top 15)")
                click.echo("-" * 80)
                agency_counts = Counter(agencies)
                for agency, count in agency_counts.most_common(15):
                    click.echo(f"{agency:20s} {count:5,} mentions")

        click.echo("\n" + "=" * 80)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
