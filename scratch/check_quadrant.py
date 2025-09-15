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
print("EXECUTIVE ORDERS SAMPLE")
print("=" * 60)

if any(col.name == "executive_orders" for col in collections):
    results = client.client.scroll(
        collection_name="executive_orders",
        limit=2,
        with_payload=True,
        with_vectors=False,
    )

    for i, point in enumerate(results[0], 1):
        print(f"\nChunk {i}:")
        print(f"  ID: {point.id}")
        if point.payload.get("metadata"):
            metadata = point.payload["metadata"]
            print(f'  Document ID: {metadata.get("document_id")}')
            print(f'  Title: {metadata.get("title", "N/A")[:60]}...')
            print(f'  Date: {metadata.get("publication_date")}')
        if point.payload.get("text"):
            print(f'  Text preview: {point.payload["text"][:100]}...')

# Check Supreme Court Opinions collection
print("\n" + "=" * 60)
print("SUPREME COURT OPINIONS SAMPLE")
print("=" * 60)

if any(col.name == "supreme_court_opinions" for col in collections):
    results = client.client.scroll(
        collection_name="supreme_court_opinions",
        limit=2,
        with_payload=True,
        with_vectors=False,
    )

    for i, point in enumerate(results[0], 1):
        print(f"\nChunk {i}:")
        print(f"  ID: {point.id}")
        if point.payload.get("metadata"):
            metadata = point.payload["metadata"]
            print(f'  Case: {metadata.get("case_name", "N/A")}')
            print(f'  Citation: {metadata.get("citation_bluebook")}')
            print(f'  Date: {metadata.get("publication_date")}')
        if point.payload.get("text"):
            print(f'  Text preview: {point.payload["text"][:100]}...')
