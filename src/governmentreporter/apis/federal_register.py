"""Federal Register API client for fetching executive orders."""

import re
import time
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

import httpx
from httpx import Response

from ..utils import get_logger
from .base import Document, GovernmentAPIClient


class FederalRegisterClient(GovernmentAPIClient):
    """Client for interacting with the Federal Register API."""

    def __init__(self):
        """Initialize the Federal Register client.

        Note: Federal Register API doesn't require authentication.
        """
        super().__init__(api_key=None)
        self.logger = get_logger(__name__)
        self.headers = {
            "User-Agent": "GovernmentReporter/0.1.0",
            "Accept": "application/json",
        }
        self.max_retries = 5
        self.retry_delay = 1.0  # Initial delay for exponential backoff

    def _get_base_url(self) -> str:
        """Return the base URL for the API."""
        return "https://www.federalregister.gov/api/v1"

    def _get_rate_limit_delay(self) -> float:
        """Return the rate limit delay in seconds between requests.

        Federal Register API has a 60 requests/minute limit.
        """
        return 1.1  # Slightly over 1 second to stay well under 60/min

    def _make_request_with_retry(
        self, url: str, params: Optional[Dict] = None
    ) -> Response:
        """Make an HTTP request with exponential backoff retry logic.

        Args:
            url: The URL to request
            params: Optional query parameters

        Returns:
            The HTTP response

        Raises:
            httpx.HTTPError: If all retries are exhausted
        """
        retry_count = 0
        delay = self.retry_delay

        while retry_count < self.max_retries:
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(url, headers=self.headers, params=params)
                    response.raise_for_status()
                    return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    retry_count += 1
                    if retry_count < self.max_retries:
                        self.logger.warning(
                            f"Rate limited. Retry {retry_count}/{self.max_retries} after {delay:.1f}s"
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                    else:
                        raise
                else:
                    raise
            except httpx.RequestError as e:
                retry_count += 1
                if retry_count < self.max_retries:
                    self.logger.warning(
                        f"Request error: {e}. Retry {retry_count}/{self.max_retries} after {delay:.1f}s"
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise

        raise httpx.HTTPError(f"Failed after {self.max_retries} retries")

    def get_executive_order_text(self, raw_text_url: str) -> str:
        """Fetch the raw text of an executive order from the provided URL.

        Args:
            raw_text_url: The URL to the raw text of the executive order

        Returns:
            The raw text content of the executive order

        Raises:
            httpx.HTTPError: If the request fails
        """
        response = self._make_request_with_retry(raw_text_url)
        text = response.text

        # Clean up HTML if present (the raw text often contains HTML markup)
        if text.startswith("<html>"):
            # Extract text between <pre> tags
            pre_match = re.search(r"<pre>(.*?)</pre>", text, re.DOTALL)
            if pre_match:
                text = pre_match.group(1)
                # Remove HTML entities
                text = text.replace("&lt;", "<").replace("&gt;", ">")
                text = text.replace("&amp;", "&").replace("&quot;", '"')
                # Remove HTML anchor tags
                text = re.sub(r"<a[^>]*>.*?</a>", "", text)

        return text.strip()

    def list_executive_orders(
        self, start_date: str, end_date: str, max_results: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """List executive orders between two dates.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_results: Maximum number of results to return (None for all)

        Yields:
            Dict containing executive order metadata

        Raises:
            httpx.HTTPError: If an API request fails
        """
        # Validate date formats
        if not self.validate_date_format(start_date):
            raise ValueError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD")
        if not self.validate_date_format(end_date):
            raise ValueError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD")

        url = f"{self.base_url}/documents"
        params = {
            "conditions[type]": "PRESDOCU",
            "conditions[presidential_document_type]": "executive_order",
            "conditions[signing_date][gte]": start_date,
            "conditions[signing_date][lte]": end_date,
            "fields[]": [
                "document_number",
                "title",
                "executive_order_number",
                "publication_date",
                "signing_date",
                "president",
                "citation",
                "html_url",
                "pdf_url",
                "full_text_xml_url",
                "body_html_url",
                "raw_text_url",
                "json_url",
            ],
            "per_page": 100,
            "page": 1,
        }

        results_count = 0

        while True:
            # Rate limiting
            time.sleep(self.rate_limit_delay)

            self.logger.info(f"Fetching page {params['page']} of executive orders...")
            response = self._make_request_with_retry(url, params)
            data = response.json()

            results = data.get("results", [])

            if not results:
                break

            for order in results:
                if max_results is not None and results_count >= max_results:
                    return

                yield order
                results_count += 1

            # Check if there are more pages
            total_pages = data.get("total_pages", 1)
            current_page = params["page"]

            self.logger.info(
                f"Processed page {current_page}/{total_pages}, "
                f"total orders so far: {results_count}"
            )

            if current_page >= total_pages:
                break

            params["page"] += 1

    def get_executive_order(self, document_number: str) -> Dict[str, Any]:
        """Fetch a specific executive order by document number.

        Args:
            document_number: The Federal Register document number

        Returns:
            Dict containing the executive order data

        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/documents/{document_number}"

        response = self._make_request_with_retry(url)
        return response.json()

    def search_documents(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
    ) -> List[Document]:
        """Search for executive orders (minimal implementation).

        Args:
            query: Search query string (not currently used)
            start_date: Optional start date filter (YYYY-MM-DD format)
            end_date: Optional end date filter (YYYY-MM-DD format)
            limit: Maximum number of results to return

        Returns:
            List of Document objects
        """
        # This is a minimal implementation to satisfy the abstract base class
        # The actual processing uses list_executive_orders directly
        return []

    def get_document(self, document_id: str) -> Document:
        """Retrieve a specific executive order by document number.

        Args:
            document_id: Document number from Federal Register

        Returns:
            Document object with full content
        """
        order_data = self.get_executive_order(document_id)

        # Get the raw text
        raw_text_url = order_data.get("raw_text_url")
        if raw_text_url:
            content = self.get_executive_order_text(raw_text_url)
        else:
            content = order_data.get("abstract", "")

        return Document(
            id=document_id,
            title=order_data.get("title", "Unknown Executive Order"),
            date=order_data.get("signing_date", ""),
            type="Executive Order",
            source="FederalRegister",
            content=content,
            metadata=order_data,
            url=order_data.get("html_url"),
        )

    def get_document_text(self, document_id: str) -> str:
        """Retrieve the plain text content of an executive order.

        Args:
            document_id: Document number from Federal Register

        Returns:
            Plain text content of the executive order
        """
        order_data = self.get_executive_order(document_id)
        raw_text_url = order_data.get("raw_text_url")

        if raw_text_url:
            return self.get_executive_order_text(raw_text_url)
        else:
            return order_data.get("abstract", "")

    def extract_basic_metadata(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic metadata from executive order data.

        Args:
            order_data: Raw executive order data from API

        Returns:
            Dict with extracted metadata
        """
        # Parse the signing date
        signing_date_str = order_data.get("signing_date", "")
        try:
            signing_date = datetime.fromisoformat(signing_date_str)
            formatted_date = signing_date.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            formatted_date = signing_date_str

        # Extract president info
        president_data = order_data.get("president", {})
        if isinstance(president_data, dict):
            president_name = president_data.get("name", "Unknown")
        else:
            president_name = str(president_data) if president_data else "Unknown"

        return {
            "document_number": order_data.get("document_number"),
            "title": order_data.get("title", ""),
            "executive_order_number": order_data.get("executive_order_number"),
            "signing_date": formatted_date,
            "president": president_name,
            "citation": order_data.get("citation", ""),
            "html_url": order_data.get("html_url", ""),
            "raw_text_url": order_data.get("raw_text_url", ""),
            "publication_date": order_data.get("publication_date", ""),
        }
