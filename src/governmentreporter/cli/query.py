"""
Query CLI command for testing semantic search.

Provides a command-line interface for testing document search
without needing to run the full MCP server.
"""

import sys
from typing import Optional

import click


@click.command()
@click.argument("query_text")
@click.option(
    "--collection",
    type=click.Choice(["scotus", "eo", "all"], case_sensitive=False),
    default="all",
    help="Which collection to search (default: all)",
)
@click.option(
    "--limit",
    type=int,
    default=5,
    help="Number of results to return (default: 5)",
)
@click.option(
    "--min-score",
    type=float,
    default=0.7,
    help="Minimum similarity score (0.0-1.0, default: 0.7)",
)
@click.option(
    "--qdrant-path",
    default="./data/qdrant/qdrant_db",
    help="Path to Qdrant database (default: ./data/qdrant/qdrant_db)",
)
@click.option(
    "--show-text",
    is_flag=True,
    help="Show full chunk text in results",
)
def query(
    query_text: str,
    collection: str,
    limit: int,
    min_score: float,
    qdrant_path: str,
    show_text: bool,
):
    """
    Search for documents using semantic similarity.

    Performs a semantic search across the vector database and returns
    the most relevant document chunks.

    Examples:
        governmentreporter query "fourth amendment search and seizure"
        governmentreporter query "executive order climate change" --collection eo
        governmentreporter query "supreme court precedent" --limit 10 --show-text
    """
    from ..database.qdrant import QdrantClient
    from ..processors.embeddings import EmbeddingGenerator

    try:
        # Initialize components
        click.echo(f"Searching for: '{query_text}'")
        click.echo(f"Collection: {collection}")
        click.echo(f"Minimum score: {min_score}\n")

        embedding_gen = EmbeddingGenerator()

        # Generate query embedding
        query_embedding = embedding_gen.generate_embedding(query_text)

        # Determine which collections to search
        if collection == "all":
            collections = ["supreme_court_opinions", "executive_orders"]
        elif collection == "scotus":
            collections = ["supreme_court_opinions"]
        else:  # eo
            collections = ["executive_orders"]

        all_results = []

        # Search each collection
        for coll_name in collections:
            try:
                client = QdrantClient(coll_name, qdrant_path)
                results = client.search(
                    query_vector=query_embedding, limit=limit, score_threshold=min_score
                )

                for result in results:
                    all_results.append(
                        {
                            "collection": coll_name,
                            "score": result.score,
                            "payload": result.payload,
                        }
                    )

            except Exception as e:
                click.echo(f"Warning: Could not search {coll_name}: {e}", err=True)

        # Sort by score
        all_results.sort(key=lambda x: x["score"], reverse=True)

        # Limit to top N
        all_results = all_results[:limit]

        if not all_results:
            click.echo("No results found.", err=True)
            sys.exit(1)

        # Display results
        click.echo(f"Found {len(all_results)} results:\n")
        click.echo("=" * 80)

        for i, result in enumerate(all_results, 1):
            score = result["score"]
            payload = result["payload"]
            coll = result["collection"]

            click.echo(f"\n[{i}] Score: {score:.4f} | Collection: {coll}")
            click.echo("-" * 80)

            # Display metadata
            if "title" in payload:
                click.echo(f"Title: {payload['title']}")
            if "date" in payload:
                click.echo(f"Date: {payload['date']}")
            if "section_label" in payload:
                click.echo(f"Section: {payload['section_label']}")
            if "document_type" in payload:
                click.echo(f"Type: {payload['document_type']}")

            # Show text if requested
            if show_text and "text" in payload:
                click.echo(f"\nText:\n{payload['text'][:500]}...")

            click.echo()

        click.echo("=" * 80)

    except KeyboardInterrupt:
        click.echo("\n\nSearch cancelled by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
