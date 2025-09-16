"""
Configuration module for the GovernmentReporter MCP server.

This module defines configuration settings for the MCP server, including
server metadata, collection names, search parameters, and other operational
settings. Configuration can be customized via environment variables or
by creating a ServerConfig instance with custom values.

Classes:
    ServerConfig: Main configuration class for the MCP server.

Environment Variables:
    MCP_SERVER_NAME: Override the default server name
    MCP_SERVER_VERSION: Override the server version
    MCP_DEFAULT_SEARCH_LIMIT: Default number of search results
    MCP_MAX_SEARCH_LIMIT: Maximum allowed search results
    QDRANT_HOST: Qdrant server host (default: localhost)
    QDRANT_PORT: Qdrant server port (default: 6333)
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ServerConfig:
    """
    Configuration settings for the GovernmentReporter MCP server.

    This class holds all configuration parameters for the MCP server,
    with sensible defaults that can be overridden via environment variables
    or constructor arguments.

    Attributes:
        server_name: Name of the MCP server for identification.
        server_version: Version string for the server.
        collections: Mapping of document types to Qdrant collection names.
        default_search_limit: Default number of results for searches.
        max_search_limit: Maximum allowed number of search results.
        qdrant_host: Host address for Qdrant server.
        qdrant_port: Port number for Qdrant server.
        qdrant_grpc_port: gRPC port for Qdrant (optional).
        embedding_model: OpenAI embedding model to use.
        embedding_dimensions: Dimensions of the embedding vectors.
        chunk_overlap_ratio: Overlap ratio for document chunking.
        cache_ttl: Cache time-to-live in seconds.
        enable_caching: Whether to enable result caching.

    Example:
        >>> config = ServerConfig(
        ...     server_name="CustomMCP",
        ...     default_search_limit=20
        ... )
    """

    # Server identification
    server_name: str = field(
        default_factory=lambda: os.getenv(
            "MCP_SERVER_NAME", "GovernmentReporter MCP Server"
        )
    )
    server_version: str = field(
        default_factory=lambda: os.getenv("MCP_SERVER_VERSION", "1.0.0")
    )

    # Collection mappings
    collections: Dict[str, str] = field(
        default_factory=lambda: {
            "scotus": "supreme_court_opinions",
            "executive_orders": "executive_orders",
            "federal_register": "federal_register_documents",  # Future expansion
            "congress": "congressional_documents",  # Future expansion
        }
    )

    # Search parameters
    default_search_limit: int = field(
        default_factory=lambda: int(os.getenv("MCP_DEFAULT_SEARCH_LIMIT", "10"))
    )
    max_search_limit: int = field(
        default_factory=lambda: int(os.getenv("MCP_MAX_SEARCH_LIMIT", "50"))
    )

    # Qdrant connection settings
    qdrant_host: str = field(
        default_factory=lambda: os.getenv("QDRANT_HOST", "localhost")
    )
    qdrant_port: int = field(
        default_factory=lambda: int(os.getenv("QDRANT_PORT", "6333"))
    )
    qdrant_grpc_port: Optional[int] = field(
        default_factory=lambda: (
            int(os.getenv("QDRANT_GRPC_PORT"))
            if os.getenv("QDRANT_GRPC_PORT")
            else None
        )
    )
    qdrant_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("QDRANT_API_KEY")
    )

    # Embedding configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Chunking configuration (matching your existing settings)
    scotus_chunk_config: Dict[str, int] = field(
        default_factory=lambda: {
            "min_tokens": 500,
            "target_tokens": 600,
            "max_tokens": 800,
            "overlap_ratio": 15,  # percentage
        }
    )
    eo_chunk_config: Dict[str, int] = field(
        default_factory=lambda: {
            "min_tokens": 240,
            "target_tokens": 340,
            "max_tokens": 400,
            "overlap_ratio": 10,  # percentage
        }
    )

    # Caching configuration
    cache_ttl: int = 3600  # 1 hour in seconds
    enable_caching: bool = field(
        default_factory=lambda: os.getenv("MCP_ENABLE_CACHE", "true").lower() == "true"
    )

    # Response formatting
    truncate_chunk_length: int = 1000  # Characters to show in search results
    include_metadata_in_results: bool = True
    format_citations_bluebook: bool = True

    # Rate limiting
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = 60

    # Logging
    log_level: str = field(
        default_factory=lambda: os.getenv("MCP_LOG_LEVEL", "INFO")
    )
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # API client configuration
    courtlistener_rate_delay: float = 0.1  # seconds between requests
    federal_register_rate_delay: float = 1.1  # seconds between requests

    # Advanced search features
    enable_semantic_reranking: bool = False
    reranking_model: Optional[str] = None
    enable_query_expansion: bool = False

    # Document retrieval
    enable_full_document_retrieval: bool = True
    max_full_document_size: int = 100000  # characters

    def get_collection_for_type(self, doc_type: str) -> Optional[str]:
        """
        Get the Qdrant collection name for a document type.

        Args:
            doc_type: The document type (e.g., "scotus", "executive_orders").

        Returns:
            The collection name if found, None otherwise.
        """
        return self.collections.get(doc_type)

    def get_all_collection_names(self) -> List[str]:
        """
        Get all configured collection names.

        Returns:
            List of all Qdrant collection names.
        """
        return list(self.collections.values())

    def validate(self) -> bool:
        """
        Validate the configuration settings.

        Returns:
            True if configuration is valid, raises ValueError otherwise.

        Raises:
            ValueError: If configuration parameters are invalid.
        """
        # Validate search limits
        if self.default_search_limit <= 0:
            raise ValueError("default_search_limit must be positive")
        if self.max_search_limit < self.default_search_limit:
            raise ValueError("max_search_limit must be >= default_search_limit")

        # Validate chunk configurations
        for config_name, config in [
            ("scotus", self.scotus_chunk_config),
            ("eo", self.eo_chunk_config),
        ]:
            if config["min_tokens"] <= 0:
                raise ValueError(f"{config_name} min_tokens must be positive")
            if config["target_tokens"] < config["min_tokens"]:
                raise ValueError(f"{config_name} target_tokens must be >= min_tokens")
            if config["max_tokens"] < config["target_tokens"]:
                raise ValueError(f"{config_name} max_tokens must be >= target_tokens")
            if not 0 <= config["overlap_ratio"] <= 100:
                raise ValueError(f"{config_name} overlap_ratio must be 0-100")

        # Validate embedding dimensions
        if self.embedding_dimensions <= 0:
            raise ValueError("embedding_dimensions must be positive")

        return True

    def to_dict(self) -> Dict:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "server_name": self.server_name,
            "server_version": self.server_version,
            "collections": self.collections,
            "default_search_limit": self.default_search_limit,
            "max_search_limit": self.max_search_limit,
            "qdrant_host": self.qdrant_host,
            "qdrant_port": self.qdrant_port,
            "embedding_model": self.embedding_model,
            "embedding_dimensions": self.embedding_dimensions,
            "scotus_chunk_config": self.scotus_chunk_config,
            "eo_chunk_config": self.eo_chunk_config,
            "cache_ttl": self.cache_ttl,
            "enable_caching": self.enable_caching,
            "log_level": self.log_level,
        }

    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()


# Singleton instance for easy import
default_config = ServerConfig()