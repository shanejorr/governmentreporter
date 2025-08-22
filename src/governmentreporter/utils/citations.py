"""Bluebook citation formatting utilities.

This module provides utilities for formatting legal citations according to the
Bluebook citation style, which is the standard for legal writing in the United States.
The Bluebook (officially "The Bluebook: A Uniform System of Citation") provides
rules for citing legal authorities in academic and professional legal documents.

The module currently focuses on court case citations, which typically follow
the format: "Volume Reporter Page (Year)" (e.g., "601 U.S. 416 (2024)").

Integration with GovernmentReporter:
    This module supports the citation needs of the legal research system:
    - Formats case citations from Court Listener API data
    - Provides standardized citation strings for legal documents
    - Supports academic and professional legal research workflows
    - Ensures consistency in legal reference formatting

Bluebook Citation Explained:
    A typical case citation has these components:
    - Volume: The volume number of the reporter series
    - Reporter: The abbreviated name of the publication (e.g., "U.S." for United States Reports)
    - Page: The page number where the case begins
    - Year: The year the case was decided (in parentheses)

    Example: "410 U.S. 113 (1973)" refers to a case in volume 410 of United States
    Reports, starting on page 113, decided in 1973.

Python Learning Notes:
    - Dict[str, Any] type hint indicates a dictionary with string keys and any value types
    - Optional[str] return type means the function can return a string or None
    - The .get() method safely accesses dictionary keys without KeyError exceptions
    - String splitting and list indexing are used for date parsing
"""

from typing import Any, Dict, Optional


def build_bluebook_citation(cluster_data: Dict[str, Any]) -> Optional[str]:
    """Build a Bluebook-formatted citation string from Court Listener cluster data.

    This function takes raw case data from the Court Listener API and formats it
    into a proper Bluebook citation. The Court Listener API provides case information
    in a structured format, and this function extracts and formats the necessary
    components for academic and professional legal citations.

    The function handles the complexity of Court Listener's data structure, which
    may include multiple citations for the same case (parallel citations) and
    different citation types. It prioritizes the primary citation and falls back
    to alternatives when necessary.

    Citation Selection Logic:
        1. Searches for citations marked as "type 1" (primary citations)
        2. If no primary citation is found, uses the first available citation
        3. Validates that all required components are present
        4. Formats according to standard Bluebook style

    Integration with GovernmentReporter:
        This function is used throughout the system for:
        - Displaying properly formatted citations in search results
        - Generating bibliographic information for legal research
        - Creating consistent citation strings for document metadata
        - Supporting academic and professional legal writing workflows

    Data Validation:
        The function performs several validation steps:
        - Ensures citation data and filing date are available
        - Verifies that volume, reporter, and page information exist
        - Validates date format and extracts year information
        - Returns None if any required component is missing

    Python Learning Notes:
        - .get() method safely accesses dictionary keys, returning None if not found
        - The 'for' loop with 'break' finds the first matching item efficiently
        - 'if not all([...])' checks that all items in a list are truthy
        - String splitting with .split() parses date strings
        - f-strings (f"...") provide clean string formatting
        - Exception handling with try/except prevents crashes on malformed data

    Args:
        cluster_data (Dict[str, Any]): A dictionary containing case information
            from the Court Listener API. Expected to have the following structure:
            - "citations": List of citation dictionaries, each containing:
                - "type": Citation type (1 for primary, others for parallel)
                - "volume": Volume number of the reporter
                - "reporter": Abbreviated reporter name (e.g., "U.S.")
                - "page": Starting page number
            - "date_filed": Date string in "YYYY-MM-DD" format

            Example structure:
            ```python
            {
                "citations": [
                    {
                        "type": 1,
                        "volume": "601",
                        "reporter": "U.S.",
                        "page": "416"
                    }
                ],
                "date_filed": "2024-05-16"
            }
            ```

    Returns:
        Optional[str]: A properly formatted Bluebook citation string in the format
            "Volume Reporter Page (Year)" (e.g., "601 U.S. 416 (2024)"), or None
            if any required components are missing or invalid.

            Returns None in these cases:
            - No citations are provided in the input data
            - No filing date is available
            - Required citation components (volume, reporter, page) are missing
            - Date format is invalid or unparseable

    Example Usage:
        ```python
        from governmentreporter.utils.citations import build_bluebook_citation

        # Example Court Listener data
        case_data = {
            "citations": [
                {
                    "type": 1,
                    "volume": "410",
                    "reporter": "U.S.",
                    "page": "113"
                }
            ],
            "date_filed": "1973-01-22"
        }

        citation = build_bluebook_citation(case_data)
        print(f"Citation: {citation}")  # Output: "410 U.S. 113 (1973)"

        # Handle missing data gracefully
        incomplete_data = {"citations": []}
        citation = build_bluebook_citation(incomplete_data)
        print(f"Citation: {citation}")  # Output: None
        ```
    """
    # Extract citations list and filing date from the cluster data
    # Using .get() prevents KeyError if keys don't exist
    citations = cluster_data.get("citations", [])
    date_filed = cluster_data.get("date_filed")

    # Early return if essential data is missing
    # This prevents processing incomplete data that can't produce a valid citation
    if not citations or not date_filed:
        return None

    # Find the primary citation (court's official citation)
    # Court Listener marks primary citations with type=1
    primary_citation = None
    for citation in citations:
        if citation.get("type") == 1:  # Primary citation type
            primary_citation = citation
            break

    # Fall back to the first available citation if no primary citation exists
    # This ensures we can still generate citations for cases with only parallel citations
    if not primary_citation:
        primary_citation = citations[0]

    # Extract the essential components of the citation
    # Each component is required for a valid Bluebook citation
    volume = primary_citation.get("volume")
    reporter = primary_citation.get("reporter")  # e.g., "U.S.", "F.3d", "S.Ct."
    page = primary_citation.get("page")

    # Validate that all required citation components are present
    # all() returns True only if all elements are truthy (not None, not empty)
    if not all([volume, reporter, page]):
        return None

    # Extract the year from the date_filed string
    # Expected format is "YYYY-MM-DD", we need just the year
    try:
        year = date_filed.split("-")[0]
    except (AttributeError, IndexError):
        # Handle cases where date_filed is None or doesn't contain expected format
        return None

    # Format and return the complete Bluebook citation
    # Standard format: "Volume Reporter Page (Year)"
    return f"{volume} {reporter} {page} ({year})"
