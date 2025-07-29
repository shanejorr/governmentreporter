#!/usr/bin/env python3
"""
Test script to verify the pipeline works with the provided SCOTUS opinion data.
This uses the pre-fetched JSON data instead of making live API calls.
"""

import json

from src.governmentreporter.apis.court_listener import CourtListenerClient
from src.governmentreporter.database import ChromaDBClient
from src.governmentreporter.metadata import GeminiMetadataGenerator
from src.governmentreporter.utils import GoogleEmbeddingsClient

# Pre-fetched data from the provided JSON response
SAMPLE_OPINION_DATA = {
    "resource_uri": "https://www.courtlistener.com/api/rest/v4/opinions/9973155/",
    "id": 9973155,
    "absolute_url": "/opinion/9506542/consumer-financial-protection-bureau-v-community-financial-services-assn/",
    "cluster_id": 9506542,
    "cluster": "https://www.courtlistener.com/api/rest/v4/clusters/9506542/",
    "author_id": 3200,
    "author": "https://www.courtlistener.com/api/rest/v4/people/3200/",
    "joined_by": [],
    "date_created": "2024-05-23T08:03:26.705254-07:00",
    "date_modified": "2025-07-24T12:09:51.319288-07:00",
    "author_str": "",
    "per_curiam": False,
    "joined_by_str": "",
    "type": "010combined",
    "sha1": "aa9de569c62bf55f3d9842455487d29cd2a7e2f5",
    "page_count": 58,
    "download_url": "https://www.supremecourt.gov/opinions/23pdf/601us2r21_db8e.pdf",
    "local_path": "pdf/2024/05/16/consumer_financial_protection_bureau_v._community_financial_services_assn._1.pdf",
    "plain_text": """                   PRELIMINARY PRINT

             Volume 601 U. S. Part 2
                             Pages 416–471




       OFFICIAL REPORTS
                                    OF


   THE SUPREME COURT
                                May 16, 2024


Page Proof Pending Publication


                   REBECCA A. WOMELDORF
                           reporter of decisions




    NOTICE: This preliminary print is subject to formal revision before
  the bound volume is published. Users are requested to notify the Reporter
  of Decisions, Supreme Court of the United States, Washington, D.C. 20543,
  pio@supremecourt.gov, of any typographical or other formal errors.
416                     OCTOBER TERM, 2023

                                 Syllabus


  CONSUMER FINANCIAL PROTECTION BUREAU
   et al. v. COMMUNITY FINANCIAL SERVICES
     ASSOCIATION OF AMERICA, LTD., et al.
certiorari to the united states court of appeals for
                  the fth circuit
      No. 22–448. Argued October 3, 2023—Decided May 16, 2024
The Constitution gives Congress control over the public fsc subject to the
  command that "[n]o Money shall be drawn from the Treasury, but in
  Consequence of Appropriations made by Law." Art. I, § 9, cl. 7. For
  most federal agencies, Congress provides funding through annual appro-
  priations. For the Consumer Financial Protection Bureau, however,
  Congress provided a standing source of funding outside the ordinary
  annual appropriations process. Specifcally, Congress authorized the
  Bureau to draw from the Federal Reserve System an amount that its
  Director deems "reasonably necessary to carry out" the Bureau's duties,
  subject only to an infation-adjusted cap. 12 U. S. C. §§ 5497(a)(1), (2).
  In this case, several trade associations representing payday lenders and
Page Proof Pending Publication
  credit-access businesses challenged regulations issued by the Bureau
  pertaining to high-interest consumer loans on statutory and constitu-
  tional grounds. As relevant here, the Fifth Circuit accepted the associ-
  ations' argument that the Bureau's funding mechanism violates the Ap-
  propriations Clause.
Held: Congress' statutory authorization allowing the Bureau to draw money
 from the earnings of the Federal Reserve System to carry out the Bu-
 reau's duties satisfes the Appropriations Clause. Pp. 424–438, 441.""",
}


def test_pipeline():
    """Test the complete pipeline with the sample data."""
    print("Testing SCOTUS Opinion Processing Pipeline")
    print("=" * 50)

    # Step 1: Extract basic metadata using CourtListenerClient
    print("1. Testing basic metadata extraction...")
    # Use dummy token for testing since we're not making API calls
    court_client = CourtListenerClient(token="dummy_token_for_testing")
    basic_metadata = court_client.extract_basic_metadata(SAMPLE_OPINION_DATA)

    print(f"   ✅ Opinion ID: {basic_metadata['id']}")
    print(f"   ✅ Date: {basic_metadata['date']}")
    print(f"   ✅ Text length: {len(basic_metadata['plain_text'])} characters")
    print(f"   ✅ Author ID: {basic_metadata['author_id']}")

    # Step 2: Test Gemini metadata generation (truncated text for testing)
    print("\n2. Testing Gemini metadata generation...")
    try:
        metadata_generator = GeminiMetadataGenerator(api_key="dummy_key_for_testing")

        # Use a shorter excerpt for testing to avoid API costs
        test_text = basic_metadata["plain_text"][:3000] + "..."
        ai_metadata = metadata_generator.generate_scotus_metadata(test_text)

        print(f"   ✅ Summary: {ai_metadata.get('summary', 'N/A')[:100]}...")
        print(f"   ✅ Topics: {ai_metadata.get('topics', [])}")
        print(f"   ✅ Author: {ai_metadata.get('author', 'N/A')}")
        print(f"   ✅ Majority: {ai_metadata.get('majority', [])}")
        print(f"   ✅ Minority: {ai_metadata.get('minority', [])}")

    except Exception as e:
        print(f"   ❌ Gemini metadata generation failed: {e}")
        # Use mock data for testing
        ai_metadata = {
            "summary": "Mock summary for testing pipeline",
            "topics": [
                "constitutional law",
                "appropriations clause",
                "federal agencies",
            ],
            "author": "Thomas",
            "majority": [
                "Roberts",
                "Thomas",
                "Sotomayor",
                "Kagan",
                "Kavanaugh",
                "Barrett",
                "Jackson",
            ],
            "minority": ["Alito", "Gorsuch"],
        }
        print("   ℹ️  Using mock metadata for pipeline testing")

    # Step 3: Test embeddings generation
    print("\n3. Testing embeddings generation...")
    try:
        embeddings_client = GoogleEmbeddingsClient(api_key="dummy_key_for_testing")

        # Use shorter text for testing
        test_text = basic_metadata["plain_text"][:1000]
        embedding = embeddings_client.generate_embedding(test_text)

        print(f"   ✅ Generated embedding with {len(embedding)} dimensions")

    except Exception as e:
        print(f"   ❌ Embeddings generation failed: {e}")
        # Use mock embedding for testing
        embedding = [0.1] * 768  # Mock 768-dimensional embedding
        print("   ℹ️  Using mock embedding for pipeline testing")

    # Step 4: Test ChromaDB storage
    print("\n4. Testing ChromaDB storage...")
    try:
        db_client = ChromaDBClient()

        # Combine metadata
        combined_metadata = {**basic_metadata, **ai_metadata}
        final_metadata = {
            k: v for k, v in combined_metadata.items() if k != "plain_text"
        }

        # Store in database
        db_client.store_scotus_opinion(
            opinion_id=str(basic_metadata["id"]),
            plain_text=basic_metadata["plain_text"],
            embedding=embedding,
            metadata=final_metadata,
        )

        print("   ✅ Successfully stored in ChromaDB")

        # Test retrieval
        retrieved = db_client.get_opinion_by_id(str(basic_metadata["id"]))
        if retrieved:
            print("   ✅ Successfully retrieved from ChromaDB")
            print(f"      - Retrieved ID: {retrieved['id']}")
            print(f"      - Document length: {len(retrieved['document'])} characters")
            print(f"      - Metadata keys: {list(retrieved['metadata'].keys())}")
        else:
            print("   ❌ Failed to retrieve from ChromaDB")

    except Exception as e:
        print(f"   ❌ ChromaDB storage failed: {e}")

    print("\n" + "=" * 50)
    print("Pipeline test completed!")


if __name__ == "__main__":
    test_pipeline()
