"""Court Listener API client for fetching US federal court opinions."""

import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from ..utils.config import get_court_listener_token


class CourtListenerClient:
    """Client for interacting with the Court Listener API."""
    
    BASE_URL = "https://www.courtlistener.com/api/rest/v4"
    
    def __init__(self, token: Optional[str] = None):
        """Initialize the Court Listener client.
        
        Args:
            token: API token. If None, will fetch from environment.
        """
        self.token = token or get_court_listener_token()
        self.headers = {
            "Authorization": f"Token {self.token}",
            "User-Agent": "GovernmentReporter/0.1.0"
        }
        
    def get_opinion(self, opinion_id: int) -> Dict[str, Any]:
        """Fetch a specific opinion by ID.
        
        Args:
            opinion_id: The Court Listener opinion ID
            
        Returns:
            Dict containing the opinion data
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = f"{self.BASE_URL}/opinions/{opinion_id}/"
        
        with httpx.Client() as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
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