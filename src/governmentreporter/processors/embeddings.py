"""
Embedding generation for semantic search.

This module provides functionality to generate vector embeddings from text using
OpenAI's text-embedding models. These embeddings enable semantic search capabilities
in vector databases like Qdrant, allowing users to find documents based on meaning
rather than exact keyword matches.

The module focuses on:
    - Efficient embedding generation using OpenAI's API
    - Batch processing for large document sets
    - Retry logic and error handling for API resilience
    - Support for the text-embedding-3-small model (1536 dimensions)

Python Learning Notes:
    - Vector embeddings are numerical representations of text meaning
    - The OpenAI client handles API authentication and requests
    - Batch processing reduces API calls and improves performance
    - Retry logic ensures reliability when dealing with network issues
    - Type hints clarify expected inputs and outputs
"""

import logging
import time
from typing import List, Optional

from openai import OpenAI

from ..utils.config import get_openai_api_key

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Handles generation of embeddings using OpenAI's text-embedding models.

    This class provides methods to generate embeddings for text chunks,
    with support for batch processing and retry logic. Embeddings are
    vector representations of text that capture semantic meaning, enabling
    similarity search in vector databases.

    The text-embedding-3-small model produces 1536-dimensional vectors that
    balance quality with efficiency. These vectors can be used to find
    semantically similar documents even when they don't share exact keywords.

    Attributes:
        api_key (str): OpenAI API key for authentication
        client (OpenAI): OpenAI client instance for API calls
        model (str): The embedding model to use (text-embedding-3-small)
        dimension (int): Vector dimension size (1536 for text-embedding-3-small)

    Example:
        # Initialize the generator
        generator = EmbeddingGenerator()

        # Generate embedding for a single text
        text = "The Supreme Court held that..."
        embedding = generator.generate_embedding(text)
        print(f"Embedding dimension: {len(embedding)}")  # 1536

        # Generate embeddings for multiple texts efficiently
        texts = ["First document...", "Second document...", "Third document..."]
        embeddings = generator.generate_batch_embeddings(texts)
        print(f"Generated {len(embeddings)} embeddings")

    Python Learning Notes:
        - __init__ method initializes the class instance
        - Instance variables (self.x) store state across method calls
        - Optional parameters provide flexibility with defaults
        - Logging helps debug issues in production
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the embedding generator with OpenAI API.

        Sets up the OpenAI client and configures the embedding model.
        If no API key is provided, it attempts to load it from environment
        variables using the config utility.

        Args:
            api_key (Optional[str]): OpenAI API key for authentication.
                If not provided, will attempt to load from environment
                variable OPENAI_API_KEY via get_openai_api_key().

        Raises:
            ValueError: If no API key is provided and none found in environment

        Python Learning Notes:
            - Optional[str] means the parameter can be a string or None
            - The 'or' operator returns the first truthy value
            - Instance variables are prefixed with self
        """
        self.api_key = api_key or get_openai_api_key()
        self.client = OpenAI(api_key=self.api_key)
        self.model = "text-embedding-3-small"
        self.dimension = 1536  # Dimension for text-embedding-3-small

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text chunk.

        This method converts text into a vector representation that captures
        its semantic meaning. The resulting vector can be used for similarity
        searches in vector databases.

        The method includes retry logic to handle temporary API failures,
        with exponential backoff between retries to avoid overwhelming the API.

        Args:
            text (str): Text to generate embedding for. Should be non-empty
                and within the model's token limit (approximately 8,000 tokens
                for text-embedding-3-small).

        Returns:
            List[float]: Vector embedding with 1536 dimensions. Each float
                represents a dimension in the semantic space.

        Raises:
            Exception: If embedding generation fails after all retry attempts.
                This could be due to API errors, network issues, or invalid input.

        Example:
            generator = EmbeddingGenerator()

            # Generate embedding for legal text
            text = "The Fourth Amendment protects against unreasonable searches"
            embedding = generator.generate_embedding(text)

            # Use embedding for similarity search
            similar_docs = vector_db.search(embedding, top_k=10)

        Python Learning Notes:
            - try/except blocks handle exceptions gracefully
            - range(n) generates numbers from 0 to n-1
            - Exponential backoff (delay *= 2) reduces API load
            - f-strings (f"...") format strings with variables
        """
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(input=text, model=self.model)
                return response.data[0].embedding

            except Exception as e:
                logger.warning(
                    f"Embedding generation attempt {attempt + 1} failed: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise

    def generate_batch_embeddings(
        self, texts: List[str], batch_size: int = 20
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple text chunks in batches.

        OpenAI's API supports batch embedding generation which is more efficient
        than individual requests. This method processes multiple texts in a single
        API call when possible, significantly reducing latency and API usage.

        If a batch fails, the method falls back to individual generation for that
        batch to ensure all texts get processed, even if some cause errors.

        Args:
            texts (List[str]): List of text chunks to generate embeddings for.
                Each text should be within the model's token limit.
            batch_size (int): Number of texts to process in each API call.
                Default is 20, which balances efficiency with API limits.
                Maximum supported by API is typically 2048.

        Returns:
            List[List[float]]: List of embedding vectors, one for each input text.
                Order is preserved - the nth embedding corresponds to the nth input text.
                Each embedding is a 1536-dimensional vector.

        Example:
            generator = EmbeddingGenerator()

            # Process multiple documents efficiently
            documents = [
                "First Amendment protects freedom of speech",
                "Second Amendment addresses the right to bear arms",
                "Fourth Amendment protects against unreasonable searches"
            ]

            embeddings = generator.generate_batch_embeddings(documents)

            # Store embeddings with documents
            for doc, embedding in zip(documents, embeddings):
                vector_db.insert(doc, embedding)

        Python Learning Notes:
            - List slicing [i:i+n] extracts a portion of the list
            - zip() pairs elements from multiple sequences
            - extend() adds all elements from another list
            - Fallback logic ensures robustness when APIs fail
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            try:
                response = self.client.embeddings.create(input=batch, model=self.model)

                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

                # Small delay to respect rate limits
                if i + batch_size < len(texts):
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"Batch embedding generation failed: {e}")
                # Fall back to individual generation for this batch
                for text in batch:
                    try:
                        embedding = self.generate_embedding(text)
                        embeddings.append(embedding)
                    except Exception as e2:
                        logger.error(f"Individual embedding generation failed: {e2}")
                        # Use zero vector as fallback
                        embeddings.append([0.0] * self.dimension)

        return embeddings
