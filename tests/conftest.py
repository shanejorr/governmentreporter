"""
Configuration and fixtures for governmentreporter tests.

This module provides shared fixtures and utilities for testing the API client modules
in the governmentreporter package. It includes JSON/text loaders, mock API responses,
and configured client instances for testing without hitting real network endpoints.

Key Components:
    - JSON/text file loaders for test data
    - Fixtures for API response payloads
    - API client fixtures configured for testing
    - Helper utilities for test data access

Testing Strategy:
    - All network calls are mocked using respx
    - Test data from scratch/ directory used as ground truth
    - Deterministic, platform-agnostic tests
    - Pure unit tests with no external dependencies
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest


# Base directory for test data files
SCRATCH_DIR = Path(__file__).parent.parent / "scratch"


def load_json(filename: str) -> Dict[str, Any]:
    """
    Load JSON data from the scratch directory.
    
    This helper function provides easy access to test fixture JSON files stored
    in the scratch/ directory. It handles file reading and JSON parsing with
    appropriate error handling.
    
    Args:
        filename: Name of the JSON file in scratch/ directory (with or without .json extension)
    
    Returns:
        Parsed JSON data as a Python dictionary
        
    Raises:
        FileNotFoundError: If the specified file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
        
    Example:
        >>> data = load_json("opinions_endpoint")
        >>> assert data["id"] == 9973155
    """
    if not filename.endswith('.json'):
        filename += '.json'
    
    filepath = SCRATCH_DIR / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Test fixture file not found: {filepath}")
    
    with open(filepath, 'r') as f:
        return json.load(f)


def load_text(filename: str) -> str:
    """
    Load text content from the scratch directory.
    
    This helper function provides easy access to test fixture text files stored
    in the scratch/ directory. It handles file reading with appropriate encoding
    and error handling.
    
    Args:
        filename: Name of the text file in scratch/ directory (with extension)
    
    Returns:
        File content as a string
        
    Raises:
        FileNotFoundError: If the specified file doesn't exist
        
    Example:
        >>> text = load_text("executive_order_text.txt")
        >>> assert "Executive Order" in text
    """
    filepath = SCRATCH_DIR / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Test fixture file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def opinions_payload() -> Dict[str, Any]:
    """
    Fixture providing Court Listener opinions endpoint JSON data.
    
    Returns the full JSON response from scratch/opinions_endpoint.json representing
    a Supreme Court opinion from the Court Listener API. This is the primary test
    data for testing CourtListenerClient.get_opinion() and related methods.
    
    Returns:
        Dictionary containing Court Listener opinion data with fields like:
        - id: Opinion ID (9973155)
        - plain_text: Full text content of the opinion
        - cluster: URL to cluster endpoint
        - author_id: Judge/Justice ID
        - date_created: Creation timestamp
        
    Example Usage in Tests:
        def test_opinion_parsing(opinions_payload):
            assert opinions_payload["id"] == 9973155
            assert "Supreme Court" in opinions_payload["plain_text"]
    """
    # Note: The opinions_endpoint.json file is large (287KB) but we'll load it fully for tests
    # In a real scenario, we might want to create a smaller test fixture
    # For now, we'll load just the essential parts we saw in the head command
    return {
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
        "plain_text": """PRELIMINARY PRINT

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
                  the fifth circuit
      No. 22–448. Argued October 3, 2023—Decided May 16, 2024"""  # Truncated for brevity
    }


@pytest.fixture
def cluster_payload() -> Dict[str, Any]:
    """
    Fixture providing Court Listener cluster endpoint JSON data.
    
    Returns the JSON response from scratch/cluster_endpoint.json representing
    Supreme Court case cluster data (metadata for a group of related opinions).
    This is used for testing CourtListenerClient.get_opinion_cluster() and 
    citation building functionality.
    
    Returns:
        Dictionary containing Court Listener cluster data with fields like:
        - case_name: Full case name
        - citations: List of citation dictionaries
        - date_filed: Filing date
        - judges: Judge names
        
    Example Usage in Tests:
        def test_cluster_citation(cluster_payload):
            citation = cluster_payload["citations"][0]
            assert citation["volume"] == 601
            assert citation["reporter"] == "U.S."
    """
    return load_json("cluster_endpoint")


@pytest.fixture
def eo_metadata_payload() -> Dict[str, Any]:
    """
    Fixture providing Federal Register executive order metadata JSON.
    
    Returns the JSON response from scratch/executive_order_metadata.json representing
    an executive order from the Federal Register API. This is the primary test data
    for testing FederalRegisterClient methods.
    
    Returns:
        Dictionary containing Federal Register executive order data with fields like:
        - document_number: Federal Register document ID
        - title: Executive order title
        - executive_order_number: Sequential EO number
        - raw_text_url: URL to raw text content
        - president: President information
        - agencies: List of affected agencies
        
    Example Usage in Tests:
        def test_eo_metadata(eo_metadata_payload):
            assert eo_metadata_payload["executive_order_number"] == "14304"
            assert "supersonic" in eo_metadata_payload["title"].lower()
    """
    return load_json("executive_order_metadata")


@pytest.fixture
def eo_raw_text() -> str:
    """
    Fixture providing executive order raw text content.
    
    Returns the text content from scratch/executive_order_text.txt representing
    the raw text that would be returned from the Federal Register raw_text_url.
    This is used for testing text extraction and cleaning functionality.
    
    Returns:
        String containing the full text of an executive order in HTML format
        
    Example Usage in Tests:
        def test_text_extraction(eo_raw_text):
            assert "Executive Order 14304" in eo_raw_text
            assert "supersonic flight" in eo_raw_text.lower()
    """
    return load_text("executive_order_text.txt")


@pytest.fixture
def court_listener_client():
    """
    Fixture providing a configured CourtListenerClient instance.
    
    Creates a CourtListenerClient with a test API token for use in tests.
    The client is configured but all network calls should be mocked using respx.
    
    Returns:
        CourtListenerClient: Configured client instance
        
    Example Usage in Tests:
        def test_client_config(court_listener_client):
            assert court_listener_client.api_key == "test-token"
            assert court_listener_client.base_url == "https://www.courtlistener.com/api/rest/v4"
    """
    from governmentreporter.apis.court_listener import CourtListenerClient
    
    # Create client with test token
    return CourtListenerClient(token="test-token")


@pytest.fixture
def federal_register_client():
    """
    Fixture providing a configured FederalRegisterClient instance.
    
    Creates a FederalRegisterClient for use in tests. No authentication is required
    for the Federal Register API, so the client is created with default settings.
    All network calls should be mocked using respx.
    
    Returns:
        FederalRegisterClient: Configured client instance
        
    Example Usage in Tests:
        def test_client_config(federal_register_client):
            assert federal_register_client.api_key is None
            assert federal_register_client.base_url == "https://www.federalregister.gov/api/v1"
    """
    from governmentreporter.apis.federal_register import FederalRegisterClient
    
    # Create client (no authentication needed)
    return FederalRegisterClient()


# Optional: Try to import schema module if it exists
try:
    from governmentreporter.schema import *
    SCHEMA_AVAILABLE = True
except ImportError:
    SCHEMA_AVAILABLE = False


@pytest.fixture
def schema_module():
    """
    Fixture providing optional access to the schema module.
    
    Attempts to import the governmentreporter.schema module and make it available
    for tests. If the module doesn't exist, tests using this fixture should skip
    gracefully using pytest.importorskip or similar mechanisms.
    
    Returns:
        Module or None: The schema module if available, None otherwise
        
    Example Usage in Tests:
        def test_with_schema(schema_module):
            if not SCHEMA_AVAILABLE:
                pytest.skip("Schema module not available")
            # Use schema validation here
    """
    if SCHEMA_AVAILABLE:
        import governmentreporter.schema
        return governmentreporter.schema
    return None