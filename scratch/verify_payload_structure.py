"""
Verification script to test that payload structure matches expectations.

This script helps verify that the payload structure from build_payloads_from_document
matches what the QdrantIngestionClient expects.
"""

from governmentreporter.apis.base import Document
from governmentreporter.processors.build_payloads import build_payloads_from_document


def verify_payload_structure():
    """Verify that build_payloads returns the expected structure."""
    # Create a minimal test document
    test_doc = Document(
        id="test_12345",
        title="Test v. Case",
        content="This is a test opinion. Section I. This is section one content.",
        date="2024-01-15",
        source="CourtListener",
        type="Supreme Court Opinion",
        url="https://example.com/test",
        metadata={"case_name": "Test v. Case", "type": "010combined"},
    )

    print("Building payloads from test document...")
    payloads = build_payloads_from_document(test_doc)

    if not payloads:
        print("❌ ERROR: No payloads generated!")
        return False

    print(f"✓ Generated {len(payloads)} payload(s)")

    # Check first payload structure
    first_payload = payloads[0]
    print("\nVerifying payload structure...")

    # Check required top-level fields
    required_fields = ["id", "text", "metadata"]
    for field in required_fields:
        if field not in first_payload:
            print(f"❌ ERROR: Missing required field '{field}'")
            return False
        print(f"✓ Field '{field}' exists")

    # Check that text is non-empty
    if not first_payload["text"]:
        print("❌ ERROR: Text field is empty!")
        return False
    print(f"✓ Text field is non-empty (length: {len(first_payload['text'])})")

    # Check that metadata contains expected fields
    metadata = first_payload["metadata"]
    if not isinstance(metadata, dict):
        print("❌ ERROR: Metadata is not a dictionary!")
        return False
    print(f"✓ Metadata is a dictionary with {len(metadata)} fields")

    # Show structure
    print("\n" + "=" * 60)
    print("PAYLOAD STRUCTURE:")
    print("=" * 60)
    print(f"ID: {first_payload['id']}")
    print(f"Text preview: {first_payload['text'][:100]}...")
    print(f"Metadata keys: {list(metadata.keys())[:10]}")
    print("=" * 60)

    print("\n✅ SUCCESS: Payload structure is correct!")
    return True


if __name__ == "__main__":
    verify_payload_structure()
