"""Bluebook citation formatting utilities."""

from typing import Any, Dict, List, Optional


def build_bluebook_citation(cluster_data: Dict[str, Any]) -> Optional[str]:
    """Build bluebook citation string from cluster data.

    Args:
        cluster_data: Cluster data from Court Listener API

    Returns:
        Bluebook formatted citation string like "601 U.S. 416 (2024)" or None if incomplete
    """
    citations = cluster_data.get("citations", [])
    date_filed = cluster_data.get("date_filed")

    if not citations or not date_filed:
        return None

    # Find the primary citation (usually the first one, or the one with type 1)
    primary_citation = None
    for citation in citations:
        if citation.get("type") == 1:  # Primary citation type
            primary_citation = citation
            break

    if not primary_citation:
        # Fall back to first citation if no primary type found
        primary_citation = citations[0]

    volume = primary_citation.get("volume")
    reporter = primary_citation.get("reporter")
    page = primary_citation.get("page")

    if not all([volume, reporter, page]):
        return None

    # Extract year from date_filed (format: "2024-05-16")
    try:
        year = date_filed.split("-")[0]
    except (AttributeError, IndexError):
        return None

    # Format as bluebook citation
    return f"{volume} {reporter} {page} ({year})"


def extract_cited_cases(opinions_cited: List[Dict[str, Any]]) -> List[str]:
    """Extract cited case names from opinions_cited array.

    Args:
        opinions_cited: Array of cited opinion objects from Court Listener

    Returns:
        List of case names or citation strings for cited cases
    """
    cited_cases = []

    for opinion in opinions_cited:
        # Try to get case name from cluster info if available
        cluster_info = opinion.get("cluster", {})
        case_name = cluster_info.get("case_name")

        if case_name:
            cited_cases.append(case_name.strip())
        else:
            # Fall back to citation if available
            citations = cluster_info.get("citations", [])
            if citations:
                citation = citations[0]
                volume = citation.get("volume")
                reporter = citation.get("reporter")
                page = citation.get("page")

                if all([volume, reporter, page]):
                    cited_cases.append(f"{volume} {reporter} {page}")

    return cited_cases
