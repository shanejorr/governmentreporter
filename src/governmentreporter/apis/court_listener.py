"""Court Listener API client for fetching US federal court opinions."""

import time
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

import httpx

from ..utils.citations import build_bluebook_citation
from ..utils.config import get_court_listener_token
from .base import Document, GovernmentAPIClient


class CourtListenerClient(GovernmentAPIClient):
    """Client for interacting with the Court Listener API."""

    def __init__(self, token: Optional[str] = None):
        """Initialize the Court Listener client.

        Args:
            token: API token. If None, will fetch from environment.
        """
        self.token = token or get_court_listener_token()
        self.headers = {
            "Authorization": f"Token {self.token}",
            "User-Agent": "GovernmentReporter/0.1.0",
        }
        super().__init__(api_key=self.token)

    def _get_base_url(self) -> str:
        """Return the base URL for the API."""
        return "https://www.courtlistener.com/api/rest/v4"

    def _get_rate_limit_delay(self) -> float:
        """Return the rate limit delay in seconds between requests."""
        return 0.1

    def get_opinion(self, opinion_id: int) -> Dict[str, Any]:
        """Fetch a specific opinion by ID.

        Args:
            opinion_id: The Court Listener opinion ID

        Returns:
            Dict containing the opinion data

        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/opinions/{opinion_id}/"

        with httpx.Client() as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    def search_documents(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
    ) -> List[Document]:
        """Search for Supreme Court opinions using the API.

        Args:
            query: Search query string (currently not used - returns all SCOTUS opinions)
            start_date: Optional start date filter (YYYY-MM-DD format)
            end_date: Optional end date filter (YYYY-MM-DD format)
            limit: Maximum number of results to return

        Returns:
            List of Document objects
        """
        documents = []
        for opinion_data in self.list_scotus_opinions(
            since_date=start_date or "1900-01-01",
            max_results=limit,
            rate_limit_delay=self.rate_limit_delay,
        ):
            metadata = self.extract_basic_metadata(opinion_data)

            # Get cluster data for case name and citation
            cluster_url = opinion_data.get("cluster")
            case_name = f"Opinion {metadata['id']}"  # Default fallback
            citation = None

            if cluster_url:
                try:
                    cluster_data = self.get_opinion_cluster(cluster_url)
                    case_name = cluster_data.get("case_name", case_name)
                    citation = build_bluebook_citation(cluster_data)
                    # Add cluster metadata to the opinion metadata
                    metadata["case_name"] = case_name
                    metadata["citation"] = citation
                except Exception as e:
                    print(
                        f"Warning: Failed to fetch cluster data for opinion {metadata['id']}: {str(e)}"
                    )

            doc = Document(
                id=str(metadata["id"]),
                title=case_name,
                date=metadata["date"] or "",
                type="Supreme Court Opinion",
                source="CourtListener",
                metadata=metadata,
                url=metadata.get("download_url"),
            )
            documents.append(doc)
        return documents

    def get_document(self, document_id: str) -> Document:
        """Retrieve a specific Supreme Court opinion by ID.

        Args:
            document_id: Opinion ID from CourtListener

        Returns:
            Document object with full content
        """
        opinion_data = self.get_opinion(int(document_id))
        metadata = self.extract_basic_metadata(opinion_data)

        # Get cluster data for case name and citation
        cluster_url = opinion_data.get("cluster")
        case_name = "Unknown Case"
        citation = None

        if cluster_url:
            try:
                cluster_data = self.get_opinion_cluster(cluster_url)
                case_name = cluster_data.get("case_name", "Unknown Case")
                citation = build_bluebook_citation(cluster_data)
                # Add cluster metadata to the opinion metadata
                metadata["case_name"] = case_name
                metadata["citation"] = citation
            except Exception as e:
                print(
                    f"Warning: Failed to fetch cluster data for opinion {document_id}: {str(e)}"
                )

        return Document(
            id=document_id,
            title=case_name,
            date=metadata["date"] or "",
            type="Supreme Court Opinion",
            source="CourtListener",
            content=metadata["plain_text"],
            metadata=metadata,
            url=metadata.get("download_url"),
        )

    def get_document_text(self, document_id: str) -> str:
        """Retrieve the plain text content of an opinion.

        Args:
            document_id: Opinion ID from CourtListener

        Returns:
            Plain text content of the opinion
        """
        opinion_data = self.get_opinion(int(document_id))
        return opinion_data.get("plain_text", "")

    def extract_basic_metadata(self, opinion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic metadata from opinion data.

        Args:
            opinion_data: Raw opinion data from API

        Returns:
            Dict with extracted metadata
        """
        # Parse the date_created field
        date_str = opinion_data.get("date_created", "")
        try:
            date_created = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            formatted_date = date_created.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            formatted_date = None

        return {
            "id": opinion_data.get("id"),
            "resource_uri": opinion_data.get("resource_uri"),
            "cluster_id": opinion_data.get("cluster_id"),
            "date": formatted_date,
            "plain_text": opinion_data.get("plain_text", ""),
            "author_id": opinion_data.get("author_id"),
            "type": opinion_data.get("type"),
            "page_count": opinion_data.get("page_count"),
            "download_url": opinion_data.get("download_url"),
        }

    def list_scotus_opinions(
        self,
        since_date: str = "1900-01-01",
        max_results: Optional[int] = None,
        rate_limit_delay: float = 0.1,
    ) -> Iterator[Dict[str, Any]]:
        """Iterate through all Supreme Court opinions since a given date.

        Args:
            since_date: Start date in YYYY-MM-DD format (default: 1900-01-01)
            max_results: Maximum number of results to return (None for all)
            rate_limit_delay: Delay between requests in seconds

        Yields:
            Dict containing opinion metadata (without full text)

        Raises:
            httpx.HTTPError: If an API request fails
        """
        url = f"{self.base_url}/opinions/"
        params = {
            "cluster__docket__court": "scotus",
            "date_created__gte": since_date,
            "order_by": "date_created",
        }

        results_count = 0

        with httpx.Client(timeout=30.0) as client:
            while url and (max_results is None or results_count < max_results):
                # Add rate limiting
                if rate_limit_delay > 0:
                    time.sleep(rate_limit_delay)

                print(f"Fetching: {url}")
                response = client.get(url, headers=self.headers, params=params)
                response.raise_for_status()

                data = response.json()

                # Yield each opinion in the current page
                for opinion in data.get("results", []):
                    if max_results is not None and results_count >= max_results:
                        return

                    yield opinion
                    results_count += 1

                # Get next page URL
                url = data.get("next")
                # Clear params for subsequent requests (they're included in the next URL)
                params = {}

                print(f"Progress: Processed {results_count} opinions")

    def get_scotus_opinion_count(self, since_date: str = "1900-01-01") -> int:
        """Get the total count of Supreme Court opinions since a given date.

        Args:
            since_date: Start date in YYYY-MM-DD format

        Returns:
            Total number of opinions matching the criteria

        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/opinions/"
        params = {
            "cluster__docket__court": "scotus",
            "date_created__gte": since_date,
            "count": "on",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            data = response.json()
            return data.get("count", 0)

    def get_opinion_cluster(self, cluster_url: str) -> Dict[str, Any]:
        """Fetch opinion cluster data from cluster URL.

        Args:
            cluster_url: The full URL to the cluster endpoint

        Returns:
            Dict containing the cluster data with case_name, citations, etc.

        Raises:
            httpx.HTTPError: If the API request fails
        """
        with httpx.Client(timeout=30.0) as client:
            response = client.get(cluster_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
