# uv run python scratch/check_quadrant.py
from governmentreporter.database.qdrant import QdrantClient

# Initialize client
client = QdrantClient("./qdrant_db")

# List all collections
collections = client.client.get_collections().collections
print("=" * 60)
print("QDRANT COLLECTIONS")
print("=" * 60)

for col in collections:
    info = client.client.get_collection(col.name)
    print(f"\nCollection: {col.name}")
    print(f"  Documents: {info.points_count}")
    print(f"  Vector size: {info.config.params.vectors.size}")
    print(f"  Distance metric: {info.config.params.vectors.distance}")

# Check Executive Orders collection
print("\n" + "=" * 60)
print("EXECUTIVE ORDERS DETAILED METADATA")
print("=" * 60)

if any(col.name == "executive_orders" for col in collections):
    results = client.client.scroll(
        collection_name="executive_orders",
        limit=2,
        with_payload=True,
        with_vectors=False,
    )

    for i, point in enumerate(results[0], 1):
        print(f"\nChunk {i} - Point ID: {point.id}")
        print("-" * 40)

        if point.payload.get("metadata"):
            metadata = point.payload["metadata"]

            # Document/API-extracted fields
            print("  Document/API Fields:")
            print(f'    document_id: {metadata.get("document_id")}')
            print(f'    title: {metadata.get("title", "N/A")}')
            print(f'    publication_date: {metadata.get("publication_date")}')
            print(f'    year: {metadata.get("year")}')
            print(f'    source: {metadata.get("source")}')
            print(f'    type: {metadata.get("type")}')
            print(f'    url: {metadata.get("url")}')
            print(f'    eo_number: {metadata.get("eo_number")}')

            # LLM-generated fields
            print("\n  LLM-Generated Fields:")
            print(f'    plain_language_summary: {metadata.get("plain_language_summary", "N/A")[:150]}...')
            print(f'    constitution_cited: {metadata.get("constitution_cited", [])}')
            print(f'    federal_statutes_cited: {metadata.get("federal_statutes_cited", [])}')
            print(f'    federal_regulations_cited: {metadata.get("federal_regulations_cited", [])}')
            print(f'    cases_cited: {metadata.get("cases_cited", [])}')
            print(f'    topics_or_policy_areas: {metadata.get("topics_or_policy_areas", [])}')
            print(f'    agencies_impacted: {metadata.get("agencies_impacted", [])}')

            # Chunk-specific metadata
            print("\n  Chunk Metadata:")
            print(f'    chunk_id: {metadata.get("chunk_id")}')
            print(f'    chunk_index: {metadata.get("chunk_index")}')
            print(f'    section_label: {metadata.get("section_label")}')

        if point.payload.get("text"):
            print(f'\n  Text preview: {point.payload["text"][:100]}...')

# Check Supreme Court Opinions collection
print("\n" + "=" * 60)
print("SUPREME COURT OPINIONS DETAILED METADATA")
print("=" * 60)

if any(col.name == "supreme_court_opinions" for col in collections):
    results = client.client.scroll(
        collection_name="supreme_court_opinions",
        limit=2,
        with_payload=True,
        with_vectors=False,
    )

    for i, point in enumerate(results[0], 1):
        print(f"\nChunk {i} - Point ID: {point.id}")
        print("-" * 40)

        if point.payload.get("metadata"):
            metadata = point.payload["metadata"]

            # Document/API-extracted fields
            print("  Document/API Fields:")
            print(f'    document_id: {metadata.get("document_id")}')
            print(f'    title: {metadata.get("title", "N/A")}')
            print(f'    case_name: {metadata.get("case_name", "N/A")}')
            print(f'    publication_date: {metadata.get("publication_date")}')
            print(f'    year: {metadata.get("year")}')
            print(f'    source: {metadata.get("source")}')
            print(f'    type: {metadata.get("type")}')
            print(f'    url: {metadata.get("url")}')
            print(f'    opinion_type: {metadata.get("opinion_type")}')

            # LLM-generated fields
            print("\n  LLM-Generated Fields:")
            print(f'    plain_language_summary: {metadata.get("plain_language_summary", "N/A")[:150]}...')
            print(f'    holding_plain: {metadata.get("holding_plain", "N/A")}')
            print(f'    outcome_simple: {metadata.get("outcome_simple", "N/A")}')
            print(f'    issue_plain: {metadata.get("issue_plain", "N/A")}')
            print(f'    reasoning: {metadata.get("reasoning", "N/A")[:150]}...')
            print(f'    constitution_cited: {metadata.get("constitution_cited", [])}')
            print(f'    federal_statutes_cited: {metadata.get("federal_statutes_cited", [])}')
            print(f'    federal_regulations_cited: {metadata.get("federal_regulations_cited", [])}')
            print(f'    cases_cited: {metadata.get("cases_cited", [])}')
            print(f'    topics_or_policy_areas: {metadata.get("topics_or_policy_areas", [])}')

            # Chunk-specific metadata
            print("\n  Chunk Metadata:")
            print(f'    chunk_id: {metadata.get("chunk_id")}')
            print(f'    chunk_index: {metadata.get("chunk_index")}')
            print(f'    section_label: {metadata.get("section_label")}')

        if point.payload.get("text"):
            print(f'\n  Text preview: {point.payload["text"][:100]}...')
