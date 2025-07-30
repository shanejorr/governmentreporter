"""Abstract base classes for government API clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """Base class for government documents."""
    id: str
    title: str
    date: str
    type: str
    source: str
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    url: Optional[str] = None


class GovernmentAPIClient(ABC):
    """Abstract base class for government API clients."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the API client.
        
        Args:
            api_key: Optional API key for authenticated endpoints
        """
        self.api_key = api_key
        self.base_url = self._get_base_url()
        self.rate_limit_delay = self._get_rate_limit_delay()
    
    @abstractmethod
    def _get_base_url(self) -> str:
        """Return the base URL for the API."""
        pass
    
    @abstractmethod
    def _get_rate_limit_delay(self) -> float:
        """Return the rate limit delay in seconds between requests."""
        pass
    
    @abstractmethod
    def search_documents(
        self, 
        query: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        limit: int = 10
    ) -> List[Document]:
        """Search for documents using the API.
        
        Args:
            query: Search query string
            start_date: Optional start date filter (YYYY-MM-DD format)
            end_date: Optional end date filter (YYYY-MM-DD format)
            limit: Maximum number of results to return
            
        Returns:
            List of Document objects
        """
        pass
    
    @abstractmethod
    def get_document(self, document_id: str) -> Document:
        """Retrieve a specific document by ID.
        
        Args:
            document_id: Unique identifier for the document
            
        Returns:
            Document object with full content
        """
        pass
    
    @abstractmethod
    def get_document_text(self, document_id: str) -> str:
        """Retrieve the plain text content of a document.
        
        Args:
            document_id: Unique identifier for the document
            
        Returns:
            Plain text content of the document
        """
        pass
    
    def validate_date_format(self, date_str: str) -> bool:
        """Validate date string is in YYYY-MM-DD format.
        
        Args:
            date_str: Date string to validate
            
        Returns:
            True if valid format, False otherwise
        """
        import re
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        return bool(re.match(pattern, date_str))