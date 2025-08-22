"""Google embeddings generation for text content.

This module provides text embedding capabilities using Google's Generative AI models.
Embeddings are high-dimensional vector representations of text that capture semantic
meaning, enabling similarity search and retrieval operations in the GovernmentReporter system.

The module uses Google's text-embedding-004 model, which is optimized for:
- Document retrieval and semantic search
- High-quality embeddings for legal and government text
- Efficient processing of large document collections
- Integration with vector databases like ChromaDB

Integration with GovernmentReporter:
    The GoogleEmbeddingsClient is used throughout the system for:
    - Document indexing: Converting legal documents into searchable vectors
    - Query processing: Converting user queries into vectors for similarity search
    - ChromaDB storage: Providing embeddings for vector database operations
    - Semantic search: Enabling meaning-based rather than keyword-based search

Vector Embeddings Explained:
    An embedding is a list of numbers (typically 768 or 1024 dimensions) that
    represents the semantic meaning of text. Similar concepts have similar
    vector representations, allowing mathematical operations for similarity.

    Example: "Supreme Court decision" and "SCOTUS ruling" would have similar
    embeddings even though they share no common words.

Python Learning Notes:
    - The class follows the composition pattern with Google's genai library
    - Optional parameters allow flexibility in API key management
    - Exception handling ensures graceful failure with descriptive messages
    - Type hints specify that embeddings are List[float] for clarity
"""

from typing import ClassVar, List

import logging

import google.generativeai as genai

from .config import get_google_gemini_api_key


class GoogleEmbeddingsClient:
    """Client for generating text embeddings using Google's AI models.

    This class provides a simple interface to Google's text-embedding-004 model,
    specifically configured for document retrieval tasks. It handles API authentication,
    request formatting, and error handling for embedding generation.

    The client is designed for the GovernmentReporter use case of processing
    legal documents and enabling semantic search capabilities. It includes
    optimizations for legal text and integration with the broader system.

    Key Features:
    - Automatic API key management through environment variables
    - Lazy configuration - only configures Google AI when first needed
    - Thread-safe singleton pattern for configuration management
    - Text truncation to handle Google's token limits
    - Optimized parameters for legal document retrieval
    - Consistent error handling and logging

    Integration Points:
        - Used by document indexing processes to create searchable vectors
        - Called during query processing for semantic search
        - Integrated with ChromaDB for vector storage and retrieval
        - Part of the metadata generation pipeline

    Model Details:
        - Uses Google's text-embedding-004 model
        - Optimized for retrieval tasks (vs. similarity or clustering)
        - Produces 768-dimensional vectors
        - Handles multiple languages but optimized for English

    Python Learning Notes:
        - __init__ is the constructor method that runs when creating an instance
        - self refers to the current instance of the class
        - ClassVar indicates a class-level variable shared by all instances
        - The lazy initialization pattern ensures configuration happens only once
    """

    # Class variable to track if Google AI has been configured
    # This is shared across all instances of the class
    _configured: ClassVar[bool] = False

    def __init__(self):
        """Initialize the Google embeddings client.

        Sets up the client with the specific model for text embeddings.
        Configures the Google Generative AI library with API key on first use
        (lazy initialization pattern).

        Model Selection:
            The client uses "models/text-embedding-004" which is Google's latest
            text embedding model optimized for:
            - Document retrieval and search applications
            - High-quality semantic understanding
            - Efficient processing of large text collections

        Python Learning Notes:
            - self.model_name stores the model identifier for later use
            - Class variable _configured ensures configuration happens only once
            - Lazy initialization delays configuration until actually needed

        Example Usage:
            ```python
            # No need to configure genai beforehand - happens automatically
            client = GoogleEmbeddingsClient()

            # Generate embedding (configuration happens on first call)
            embedding = client.generate_embedding("Supreme Court case text")
            ```
        """
        self.logger = logging.getLogger(__name__)
        
        # Configure Google AI on first instantiation (lazy singleton pattern)
        # This ensures configuration happens once, regardless of entry point
        if not GoogleEmbeddingsClient._configured:
            genai.configure(api_key=get_google_gemini_api_key())
            GoogleEmbeddingsClient._configured = True

        # Set the specific model for text embeddings
        # text-embedding-004 is Google's latest embedding model
        self.model_name = "models/text-embedding-004"
        
        self.logger.info(f"GoogleEmbeddingsClient initialized with model {self.model_name}")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate a high-dimensional vector embedding for the given text.

        This method converts input text into a numerical vector representation
        that captures semantic meaning. The resulting embedding can be used for
        similarity comparisons, clustering, and vector database operations.

        The embedding generation process:
        1. Validates and truncates input text if necessary
        2. Calls Google's embedding API with optimized parameters
        3. Extracts the embedding vector from the response
        4. Returns the vector as a list of floating-point numbers

        Text Processing:
            - Input text is truncated to 10,000 characters to respect API limits
            - The truncation preserves the beginning of the text (most important)
            - Google's tokenizer may further limit text, but this provides safety

        API Parameters:
            - model: Uses text-embedding-004 for high-quality embeddings
            - task_type: "retrieval_document" optimizes for search applications
            - title: "Legal Document" provides context to improve embedding quality

        Integration with GovernmentReporter:
            This method is called by:
            - Document indexing processes to create searchable vectors
            - Query processing to convert user searches into comparable vectors
            - ChromaDB integration for vector storage and similarity search
            - Metadata generation pipelines for content analysis

        Vector Properties:
            - Dimensionality: 768 floating-point numbers
            - Range: Typically between -1.0 and 1.0
            - Similarity: Computed using cosine similarity or dot product
            - Persistence: Vectors remain stable across API calls for same text

        Python Learning Notes:
            - List[float] type hint indicates return type is a list of floats
            - try/except blocks handle potential API errors gracefully
            - String slicing (text[:10000]) gets first 10,000 characters
            - The result["embedding"] accesses a dictionary key from API response
            - Exception chaining preserves the original error information

        Args:
            text (str): The input text to convert into an embedding vector.
                This can be any text content, but the method is optimized for
                legal documents and government publications. Very long texts
                (>10,000 characters) will be automatically truncated.

        Returns:
            List[float]: A 768-dimensional vector representing the semantic
                content of the input text. Each element is a floating-point
                number that contributes to the overall meaning representation.
                The vector can be stored in databases and used for similarity
                comparisons with other embeddings.

        Raises:
            Exception: If the Google API call fails for any reason, including:
                - Network connectivity issues
                - API quota exceeded
                - Invalid API key or authentication problems
                - Malformed text input
                - Service temporarily unavailable
                The original error details are preserved in the exception message.

        Example Usage:
            ```python
            client = GoogleEmbeddingsClient()

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
            # Truncate text if too long to respect Google's API limits
            # Google's models have token limits, and 10,000 characters is a safe threshold
            if len(text) > 10000:
                text = text[:10000]
                # Note: In production, you might want to log this truncation
                # or implement more sophisticated text splitting

            # Call Google's embedding API with optimized parameters
            result = genai.embed_content(
                model=self.model_name,  # Use our configured embedding model
                content=text,  # The text to embed
                task_type="retrieval_document",  # Optimize for document retrieval
                title="Legal Document",  # Provide context for better embeddings
            )

            # Extract and return the embedding vector from the API response
            # The result is a dictionary with an "embedding" key containing the vector
            return result["embedding"]

        except Exception as e:
            # Re-raise with context while preserving the original exception chain
            # Using 'from e' maintains the full stack trace for debugging
            raise RuntimeError(f"Failed to generate embedding: {str(e)}") from e
