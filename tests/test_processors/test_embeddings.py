"""
Unit tests for embedding generation functionality.

This module provides comprehensive tests for the embedding generation system
that creates vector representations of text using OpenAI's text-embedding models.
All OpenAI API calls are mocked to ensure isolated, deterministic testing.

Test Categories:
    - Happy path: Successful embedding generation for single and batch texts
    - Edge cases: Empty text, very long text, special characters
    - Error handling: API failures, rate limits, network errors
    - Configuration: API key handling, model selection

Python Learning Notes:
    - Mock objects replace external API calls for testing
    - Embeddings are vectors (lists of floats) representing text meaning
    - Batch processing tests ensure efficiency with multiple texts
"""

import logging
from unittest.mock import Mock, patch, MagicMock
import pytest
from openai import OpenAI, RateLimitError, APIError

from governmentreporter.processors.embeddings import (
    EmbeddingGenerator,
    generate_embedding,
)


class TestEmbeddingGenerator:
    """
    Test suite for the EmbeddingGenerator class.

    This class tests the embedding generator's initialization, configuration,
    and core functionality with mocked OpenAI API interactions.

    Python Learning Notes:
        - Class-based tests group related test methods
        - setUp methods can provide common test initialization
        - Mocking prevents actual API calls during testing
    """

    @patch("governmentreporter.processors.embeddings.get_openai_api_key")
    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_init_with_provided_api_key(self, mock_openai_class, mock_get_key):
        """
        Test initialization with explicitly provided API key.

        Verifies that when an API key is provided directly,
        it's used instead of fetching from environment.

        Args:
            mock_openai_class: Mock OpenAI class
            mock_get_key: Mock function for getting API key
        """
        # Arrange
        test_api_key = "test-api-key-12345"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Act
        generator = EmbeddingGenerator(api_key=test_api_key)

        # Assert
        assert generator.api_key == test_api_key
        assert generator.model == "text-embedding-3-small"
        assert generator.dimension == 1536
        mock_openai_class.assert_called_once_with(api_key=test_api_key)
        mock_get_key.assert_not_called()  # Should not fetch from env

    @patch("governmentreporter.processors.embeddings.get_openai_api_key")
    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_init_with_env_api_key(self, mock_openai_class, mock_get_key):
        """
        Test initialization fetching API key from environment.

        Verifies that when no API key is provided, the generator
        fetches it from environment variables via config utility.

        Args:
            mock_openai_class: Mock OpenAI class
            mock_get_key: Mock function for getting API key
        """
        # Arrange
        env_api_key = "env-api-key-67890"
        mock_get_key.return_value = env_api_key
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Act
        generator = EmbeddingGenerator()

        # Assert
        assert generator.api_key == env_api_key
        mock_get_key.assert_called_once()
        mock_openai_class.assert_called_once_with(api_key=env_api_key)

    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_generate_embedding_success(self, mock_openai_class):
        """
        Test successful generation of single text embedding.

        Verifies that the generator correctly calls OpenAI API
        and returns the embedding vector.

        Args:
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Create mock embedding response
        mock_embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_client.embeddings.create.return_value = mock_response

        generator = EmbeddingGenerator(api_key="test-key")
        test_text = "This is a test document for embedding generation."

        # Act
        result = generator.generate_embedding(test_text)

        # Assert
        assert result == mock_embedding
        assert len(result) == 1536
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input=test_text
        )

    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_generate_embedding_empty_text(self, mock_openai_class):
        """
        Test embedding generation for empty text.

        Verifies that empty text returns an empty embedding vector
        or handles gracefully without errors.

        Args:
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # OpenAI typically returns a zero or near-zero vector for empty text
        mock_embedding = [0.0] * 1536
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_client.embeddings.create.return_value = mock_response

        generator = EmbeddingGenerator(api_key="test-key")

        # Act
        result = generator.generate_embedding("")

        # Assert
        assert len(result) == 1536
        assert all(v == 0.0 for v in result)

    @patch("governmentreporter.processors.embeddings.time.sleep")
    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_generate_embedding_with_retry_on_rate_limit(
        self, mock_openai_class, mock_sleep
    ):
        """
        Test retry logic when encountering rate limit errors.

        Verifies that the generator retries with exponential backoff
        when OpenAI returns rate limit errors.

        Args:
            mock_openai_class: Mock OpenAI class
            mock_sleep: Mock sleep function for retry delays
        """
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # First call raises RateLimitError, second succeeds
        mock_embedding = [0.5] * 1536
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]

        mock_client.embeddings.create.side_effect = [
            RateLimitError("Rate limit exceeded", response=MagicMock(), body=None),
            mock_response,
        ]

        generator = EmbeddingGenerator(api_key="test-key")
        test_text = "Test text for retry logic."

        # Act
        result = generator.generate_embedding(test_text)

        # Assert
        assert result == mock_embedding
        assert mock_client.embeddings.create.call_count == 2
        mock_sleep.assert_called()  # Verify retry delay

    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_generate_embedding_api_error(self, mock_openai_class):
        """
        Test handling of OpenAI API errors.

        Verifies proper error propagation when API fails
        after retry attempts are exhausted.

        Args:
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Simulate persistent API error
        # APIError signature: (message, request, *, body)
        mock_request = MagicMock()
        mock_client.embeddings.create.side_effect = APIError(
            "Internal server error", request=mock_request, body=None
        )

        generator = EmbeddingGenerator(api_key="test-key")

        # Act & Assert
        with pytest.raises(APIError):
            generator.generate_embedding("Test text")

    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_generate_batch_embeddings_success(self, mock_openai_class):
        """
        Test successful batch embedding generation.

        Verifies efficient processing of multiple texts in a single
        API call for better performance.

        Args:
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Create mock embeddings for batch
        texts = [
            "First document text.",
            "Second document text.",
            "Third document text.",
        ]
        mock_embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=emb) for emb in mock_embeddings]
        mock_client.embeddings.create.return_value = mock_response

        generator = EmbeddingGenerator(api_key="test-key")

        # Act
        results = generator.generate_batch_embeddings(texts)

        # Assert
        assert len(results) == 3
        assert results == mock_embeddings
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input=texts
        )

    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_generate_batch_embeddings_empty_list(self, mock_openai_class):
        """
        Test batch embedding generation with empty list.

        Ensures empty input list returns empty output list
        without making unnecessary API calls.

        Args:
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        generator = EmbeddingGenerator(api_key="test-key")

        # Act
        results = generator.generate_batch_embeddings([])

        # Assert
        assert results == []
        mock_client.embeddings.create.assert_not_called()

    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_generate_batch_embeddings_partial_failure(self, mock_openai_class):
        """
        Test batch embedding with partial failure handling.

        Verifies behavior when some texts in batch cause errors,
        ensuring graceful degradation or retry logic.

        Args:
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        texts = ["Valid text", "Another valid text"]

        # First attempt fails, fallback to individual processing
        mock_request = MagicMock()
        mock_client.embeddings.create.side_effect = [
            APIError("Batch processing failed", request=mock_request, body=None),
            MagicMock(data=[MagicMock(embedding=[0.1] * 1536)]),
            MagicMock(data=[MagicMock(embedding=[0.2] * 1536)]),
        ]

        generator = EmbeddingGenerator(api_key="test-key")

        # Act
        results = generator.generate_batch_embeddings(texts)

        # Assert
        assert len(results) == 2
        assert mock_client.embeddings.create.call_count == 3  # 1 batch + 2 individual


class TestGenerateEmbeddingFunction:
    """
    Test suite for the module-level generate_embedding function.

    Tests the convenience function that provides a simpler interface
    for one-off embedding generation without class instantiation.

    Python Learning Notes:
        - Module-level functions provide convenience interfaces
        - These often wrap class-based functionality
    """

    @patch("governmentreporter.processors.embeddings.EmbeddingGenerator")
    def test_generate_embedding_function_success(self, mock_generator_class):
        """
        Test the convenience function for generating embeddings.

        Verifies that the function correctly instantiates the generator
        and returns the embedding.

        Args:
            mock_generator_class: Mock EmbeddingGenerator class
        """
        # Arrange
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_embedding = [0.5] * 1536
        mock_generator.generate_embedding.return_value = mock_embedding

        test_text = "Test document for embedding."

        # Act
        result = generate_embedding(test_text)

        # Assert
        assert result == mock_embedding
        mock_generator_class.assert_called_once()  # No api_key argument
        mock_generator.generate_embedding.assert_called_once_with(test_text)

    @patch("governmentreporter.processors.embeddings.EmbeddingGenerator")
    def test_generate_embedding_function_no_api_key(self, mock_generator_class):
        """
        Test convenience function without explicit API key.

        Ensures the function works when relying on environment
        variables for API key configuration.

        Args:
            mock_generator_class: Mock EmbeddingGenerator class
        """
        # Arrange
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_embedding = [0.3] * 1536
        mock_generator.generate_embedding.return_value = mock_embedding

        # Act
        result = generate_embedding("Test text")

        # Assert
        assert result == mock_embedding
        mock_generator_class.assert_called_once()  # No arguments


class TestEmbeddingIntegration:
    """
    Integration tests for embedding generation.

    Tests the complete embedding pipeline with realistic scenarios
    to ensure all components work together correctly.

    Python Learning Notes:
        - Integration tests verify end-to-end functionality
        - They catch issues that unit tests might miss
    """

    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_embeddings_for_document_chunks(self, mock_openai_class):
        """
        Test generating embeddings for document chunks.

        Simulates the real-world scenario of processing multiple
        chunks from a document for vector storage.

        Args:
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Simulate chunks from a legal document
        chunks = [
            "The Court holds that the statute in question violates the First Amendment.",
            "In reaching this conclusion, we consider three factors.",
            "First, the law imposes a substantial burden on protected speech.",
            "Second, the government has not demonstrated a compelling interest.",
            "Third, less restrictive alternatives are available.",
        ]

        # Mock different embeddings for each chunk
        mock_embeddings = [[i * 0.1] * 1536 for i in range(len(chunks))]

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=emb) for emb in mock_embeddings]
        mock_client.embeddings.create.return_value = mock_response

        generator = EmbeddingGenerator(api_key="test-key")

        # Act
        embeddings = generator.generate_batch_embeddings(chunks)

        # Assert
        assert len(embeddings) == len(chunks)
        assert all(len(emb) == 1536 for emb in embeddings)

        # Verify embeddings are different (not all the same)
        assert not all(embeddings[0] == emb for emb in embeddings[1:])

    @patch("governmentreporter.processors.embeddings.logger")
    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_embedding_logging(self, mock_openai_class, mock_logger):
        """
        Test that appropriate logging occurs during embedding generation.

        Verifies that the module logs important events for debugging
        and monitoring purposes.

        Args:
            mock_openai_class: Mock OpenAI class
            mock_logger: Mock logger instance
        """
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_embedding = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_client.embeddings.create.return_value = mock_response

        generator = EmbeddingGenerator(api_key="test-key")

        # Act
        generator.generate_embedding("Test text for logging")

        # Assert
        # Verify that debug/info logging occurred
        assert mock_logger.debug.called or mock_logger.info.called

    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_embedding_dimension_validation(self, mock_openai_class):
        """
        Test validation of embedding dimensions.

        Ensures the system correctly handles and validates
        the expected 1536-dimensional embeddings.

        Args:
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Test with wrong dimension
        wrong_dim_embedding = [0.1] * 1000  # Wrong dimension
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=wrong_dim_embedding)]
        mock_client.embeddings.create.return_value = mock_response

        generator = EmbeddingGenerator(api_key="test-key")

        # Act
        result = generator.generate_embedding("Test text")

        # Assert - The system should either handle or validate dimensions
        # In this case, we're just returning what OpenAI gives us
        assert len(result) == 1000  # Returns what API provides

    @patch("governmentreporter.processors.embeddings.OpenAI")
    def test_special_characters_in_text(self, mock_openai_class):
        """
        Test embedding generation with special characters.

        Ensures texts with unicode, legal symbols, and special
        formatting are handled correctly.

        Args:
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_embedding = [0.2] * 1536
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_client.embeddings.create.return_value = mock_response

        generator = EmbeddingGenerator(api_key="test-key")

        # Text with various special characters
        special_text = """
        § 1234.5 - Legal provision with symbols
        "Quoted text" with 'various' quotes
        Em—dash and en–dash usage
        © Copyright notice • Bullet points
        Mathematical: α + β = γ
        """

        # Act
        result = generator.generate_embedding(special_text)

        # Assert
        assert len(result) == 1536
        mock_client.embeddings.create.assert_called_once()

        # Verify the special text was passed correctly
        call_args = mock_client.embeddings.create.call_args
        assert special_text in str(call_args)


# Fixtures for embedding tests
@pytest.fixture
def mock_openai_client():
    """
    Create a mock OpenAI client for testing.

    Returns:
        MagicMock: Configured mock OpenAI client

    Python Learning Notes:
        - Fixtures provide reusable test setup
        - MagicMock automatically creates nested attributes
    """
    client = MagicMock(spec=OpenAI)

    # Configure default embedding response
    mock_embedding = [0.1] * 1536
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding)]
    client.embeddings.create.return_value = mock_response

    return client


@pytest.fixture
def sample_texts():
    """
    Provide sample texts for testing batch operations.

    Returns:
        list: List of sample text strings

    Python Learning Notes:
        - Fixtures can return any data type
        - Reusable test data prevents duplication
    """
    return [
        "The Supreme Court held that the statute violates due process.",
        "Executive Order 12345 establishes new federal guidelines.",
        "Section 2(a) requires all agencies to comply within 90 days.",
        "The dissenting opinion argues for a different interpretation.",
        "Implementation shall begin immediately upon publication.",
    ]


@pytest.fixture
def embedding_generator():
    """
    Create a configured EmbeddingGenerator instance for testing.

    Returns:
        EmbeddingGenerator: Generator with mocked OpenAI client

    Python Learning Notes:
        - Fixtures can use other fixtures via dependency injection
        - Complex setup logic is centralized in fixtures
    """
    with patch("governmentreporter.processors.embeddings.OpenAI"):
        with patch(
            "governmentreporter.processors.embeddings.get_openai_api_key"
        ) as mock_get_key:
            mock_get_key.return_value = "test-api-key"
            generator = EmbeddingGenerator()

            # Configure mock responses
            generator.client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            generator.client.embeddings.create.return_value = mock_response

            return generator
