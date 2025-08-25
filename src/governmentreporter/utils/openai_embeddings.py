"""OpenAI embeddings generation for text content.

This module provides text embedding capabilities using OpenAI's models.
Embeddings are high-dimensional vector representations of text that capture semantic
meaning, enabling similarity search and retrieval operations in the GovernmentReporter system.

The module uses OpenAI's text-embedding-3-small model, which is optimized for:
- Document retrieval and semantic search
- High-quality embeddings for legal and government text
- Efficient processing of large document collections
- Integration with vector databases like Qdrant

Integration with GovernmentReporter:
    The OpenAIEmbeddingsClient is used throughout the system for:
    - Document indexing: Converting legal documents into searchable vectors
    - Query processing: Converting user queries into vectors for similarity search
    - Qdrant storage: Providing embeddings for vector database operations
    - Semantic search: Enabling meaning-based rather than keyword-based search

Vector Embeddings Explained:
    An embedding is a list of numbers (typically 1536 dimensions for OpenAI models) that
    represents the semantic meaning of text. Similar concepts have similar
    vector representations, allowing mathematical operations for similarity.

    Example: "Supreme Court decision" and "SCOTUS ruling" would have similar
    embeddings even though they share no common words.

Python Learning Notes:
    - The class follows the composition pattern with OpenAI's library
    - Optional parameters allow flexibility in API key management
    - Exception handling ensures graceful failure with descriptive messages
    - Type hints specify that embeddings are List[float] for clarity
"""

from typing import ClassVar, List
import logging

from openai import OpenAI

from .config import get_openai_api_key


class OpenAIEmbeddingsClient:
    """Client for generating text embeddings using OpenAI's models.

    This class provides a simple interface to OpenAI's text-embedding-3-small model,
    specifically configured for document retrieval tasks. It handles API authentication,
    request formatting, and error handling for embedding generation.

    The client is designed for the GovernmentReporter use case of processing
    legal documents and enabling semantic search capabilities. It includes
    optimizations for legal text and integration with the broader system.

    Key Features:
    - Automatic API key management through environment variables
    - Thread-safe client initialization
    - Text truncation to handle OpenAI's token limits
    - Optimized parameters for legal document retrieval
    - Consistent error handling and logging

    Integration Points:
        - Used by document indexing processes to create searchable vectors
        - Called during query processing for semantic search
        - Integrated with Qdrant for vector storage and retrieval
        - Part of the metadata generation pipeline

    Model Details:
        - Uses OpenAI's text-embedding-3-small model
        - Optimized for retrieval tasks with good performance/cost balance
        - Produces 1536-dimensional vectors
        - Handles multiple languages but optimized for English

    Python Learning Notes:
        - __init__ is the constructor method that runs when creating an instance
        - self refers to the current instance of the class
        - The OpenAI client is initialized once per instance
    """

    def __init__(self):
        """Initialize the OpenAI embeddings client.

        Sets up the client with the specific model for text embeddings.
        Configures the OpenAI library with API key from environment.

        Model Selection:
            The client uses "text-embedding-3-small" which is OpenAI's
            cost-effective text embedding model optimized for:
            - Document retrieval and search applications
            - High-quality semantic understanding
            - Efficient processing of large text collections
            - Good balance between cost and performance

        Python Learning Notes:
            - self.client stores the OpenAI client instance
            - self.model_name stores the model identifier for later use
            - Logger provides debugging and error tracking capabilities

        Example Usage:
            ```python
            # API key is loaded from environment automatically
            client = OpenAIEmbeddingsClient()

            # Generate embedding
            embedding = client.generate_embedding("Supreme Court case text")
            ```
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize OpenAI client with API key from environment
        self.client = OpenAI(api_key=get_openai_api_key())
        
        # Set the specific model for text embeddings
        # text-embedding-3-small is cost-effective with good performance
        self.model_name = "text-embedding-3-small"
        
        self.logger.info(f"OpenAIEmbeddingsClient initialized with model {self.model_name}")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate a high-dimensional vector embedding for the given text.

        This method converts input text into a numerical vector representation
        that captures semantic meaning. The resulting embedding can be used for
        similarity comparisons, clustering, and vector database operations.

        The embedding generation process:
        1. Validates and truncates input text if necessary
        2. Calls OpenAI's embedding API with optimized parameters
        3. Extracts the embedding vector from the response
        4. Returns the vector as a list of floating-point numbers

        Text Processing:
            - Input text is truncated to 8000 tokens (approximately 32,000 characters)
            - The truncation preserves the beginning of the text (most important)
            - OpenAI's tokenizer may further limit text based on actual token count

        API Parameters:
            - model: Uses text-embedding-3-small for cost-effective embeddings
            - input: The text to embed (automatically tokenized by OpenAI)

        Integration with GovernmentReporter:
            This method is called by:
            - Document indexing processes to create searchable vectors
            - Query processing to convert user searches into comparable vectors
            - Qdrant integration for vector storage and similarity search
            - Metadata generation pipelines for content analysis

        Vector Properties:
            - Dimensionality: 1536 floating-point numbers
            - Range: Normalized vectors with values typically between -1.0 and 1.0
            - Similarity: Computed using cosine similarity or dot product
            - Persistence: Vectors remain stable across API calls for same text

        Python Learning Notes:
            - List[float] type hint indicates return type is a list of floats
            - try/except blocks handle potential API errors gracefully
            - String slicing (text[:32000]) gets first 32,000 characters
            - The response.data[0].embedding accesses the embedding from response
            - Exception chaining preserves the original error information

        Args:
            text (str): The input text to convert into an embedding vector.
                This can be any text content, but the method is optimized for
                legal documents and government publications. Very long texts
                (>32,000 characters) will be automatically truncated.

        Returns:
            List[float]: A 1536-dimensional vector representing the semantic
                content of the input text. Each element is a floating-point
                number that contributes to the overall meaning representation.
                The vector can be stored in databases and used for similarity
                comparisons with other embeddings.

        Raises:
            RuntimeError: If the OpenAI API call fails for any reason, including:
                - Network connectivity issues
                - API quota exceeded
                - Invalid API key or authentication problems
                - Malformed text input
                - Service temporarily unavailable
                The original error details are preserved in the exception message.

        Example Usage:
            ```python
            client = OpenAIEmbeddingsClient()

            # Generate embedding for a legal document
            case_text = "The Supreme Court held that..."
            embedding = client.generate_embedding(case_text)

            print(f"Generated {len(embedding)}-dimensional vector")
            print(f"First few values: {embedding[:5]}")

            # Use embedding for similarity search
            # (Compare with other embeddings using cosine similarity)
            ```
        """
        try:
            # Truncate text if too long to respect OpenAI's token limits
            # 8000 tokens is approximately 32,000 characters for English text
            if len(text) > 32000:
                text = text[:32000]
                self.logger.debug(f"Truncated text from {len(text)} to 32000 characters")

            # Call OpenAI's embedding API
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text
            )

            # Extract and return the embedding vector from the API response
            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            # Re-raise with context while preserving the original exception chain
            # Using 'from e' maintains the full stack trace for debugging
            raise RuntimeError(f"Failed to generate embedding: {str(e)}") from e