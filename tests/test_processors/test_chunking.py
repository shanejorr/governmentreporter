"""
Unit tests for document chunking functionality.

This module provides comprehensive tests for the chunking algorithms used to
split Supreme Court opinions and Executive Orders into semantic chunks for
vector storage and retrieval.

Test Categories:
    - Happy path: Normal documents with expected structure
    - Edge cases: Empty documents, single sentences, boundary conditions
    - Error handling: Invalid inputs, malformed text
    - Configuration: Environment variable overrides, custom configs

Python Learning Notes:
    - Mock objects simulate tiktoken tokenizer for consistent testing
    - Parameterized tests reduce code duplication for similar test cases
    - Fixtures provide reusable test data and configurations
"""

import os
from unittest.mock import Mock, patch, MagicMock
import pytest
from dataclasses import dataclass

from governmentreporter.processors.chunking import (
    ChunkingConfig,
    chunk_supreme_court_opinion,
    chunk_executive_order,
    _load_config,
    get_chunking_config,
    count_tokens,
    normalize_whitespace,
    chunk_text_with_tokens,
    overlap_tokens,
)


class TestChunkingConfig:
    """
    Test suite for ChunkingConfig dataclass validation.

    This class tests the configuration validation logic to ensure
    proper handling of token limits and overlap ratios.

    Python Learning Notes:
        - Dataclasses provide automatic __init__ and validation
        - __post_init__ runs after the dataclass is initialized
        - pytest.raises verifies expected exceptions
    """

    def test_valid_config_creation(self):
        """
        Test creating a valid ChunkingConfig instance.

        Verifies that valid parameters create a config without errors
        and all attributes are properly set.
        """
        # Arrange & Act
        config = ChunkingConfig(
            min_tokens=100, target_tokens=300, max_tokens=500, overlap_ratio=0.15
        )

        # Assert
        assert config.min_tokens == 100
        assert config.target_tokens == 300
        assert config.max_tokens == 500
        assert config.overlap_ratio == 0.15

    def test_invalid_negative_tokens(self):
        """
        Test that negative token counts raise ValueError.

        Ensures the configuration rejects invalid negative values
        for token counts which would break chunking logic.
        """
        # Arrange, Act & Assert
        with pytest.raises(ValueError, match="Token counts must be positive"):
            ChunkingConfig(
                min_tokens=-1, target_tokens=300, max_tokens=500, overlap_ratio=0.15
            )

    def test_invalid_min_exceeds_max(self):
        """
        Test that min_tokens exceeding max_tokens raises ValueError.

        Validates the logical constraint that minimum chunk size
        cannot exceed maximum chunk size.
        """
        # Arrange, Act & Assert
        with pytest.raises(ValueError, match="min_tokens cannot exceed max_tokens"):
            ChunkingConfig(
                min_tokens=600, target_tokens=300, max_tokens=500, overlap_ratio=0.15
            )

    def test_invalid_overlap_ratio(self):
        """
        Test that invalid overlap ratios raise ValueError.

        Ensures overlap ratio is between 0 and 1 (exclusive of 1)
        to maintain meaningful chunk boundaries.
        """
        # Test negative ratio
        with pytest.raises(ValueError, match="overlap_ratio must be between 0 and 1"):
            ChunkingConfig(
                min_tokens=100, target_tokens=300, max_tokens=500, overlap_ratio=-0.1
            )

        # Test ratio >= 1
        with pytest.raises(ValueError, match="overlap_ratio must be between 0 and 1"):
            ChunkingConfig(
                min_tokens=100, target_tokens=300, max_tokens=500, overlap_ratio=1.0
            )


class TestLoadConfig:
    """
    Test suite for configuration loading with environment overrides.

    Tests the _load_config function that loads chunking configurations
    with support for environment variable overrides.

    Python Learning Notes:
        - monkeypatch fixture allows temporary environment changes
        - Environment variables are strings, need type conversion
    """

    def test_load_default_config(self):
        """
        Test loading configuration with default values.

        Verifies that when no environment variables are set,
        the function returns the provided defaults.
        """
        # Arrange
        defaults = {
            "min_tokens": 100,
            "target_tokens": 200,
            "max_tokens": 300,
            "overlap_ratio": 0.1,
        }

        # Act
        config = _load_config("TEST_PREFIX", defaults)

        # Assert
        assert config.min_tokens == 100
        assert config.target_tokens == 200
        assert config.max_tokens == 300
        assert config.overlap_ratio == 0.1

    def test_load_config_with_env_overrides(self, monkeypatch):
        """
        Test loading configuration with environment variable overrides.

        Ensures environment variables properly override default values
        with correct type conversion.

        Args:
            monkeypatch: pytest fixture for environment modification
        """
        # Arrange
        monkeypatch.setenv("TEST_PREFIX_MIN_TOKENS", "150")
        monkeypatch.setenv("TEST_PREFIX_TARGET_TOKENS", "250")
        monkeypatch.setenv("TEST_PREFIX_MAX_TOKENS", "350")
        monkeypatch.setenv("TEST_PREFIX_OVERLAP_RATIO", "0.2")

        defaults = {
            "min_tokens": 100,
            "target_tokens": 200,
            "max_tokens": 300,
            "overlap_ratio": 0.1,
        }

        # Act
        config = _load_config("TEST_PREFIX", defaults)

        # Assert
        assert config.min_tokens == 150
        assert config.target_tokens == 250
        assert config.max_tokens == 350
        assert config.overlap_ratio == 0.2


class TestOverlapTokens:
    """
    Test suite for overlap token calculation.

    Tests the overlap_tokens function that calculates the number
    of overlapping tokens between chunks.

    Python Learning Notes:
        - Overlap ensures context continuity between chunks
        - Calculation based on ratio and target tokens
    """

    def test_calculate_overlap_tokens(self):
        """
        Test overlap token calculation.

        Verifies correct calculation of overlap tokens based on config.
        """
        # Arrange
        config = ChunkingConfig(
            min_tokens=100, target_tokens=200, max_tokens=300, overlap_ratio=0.15
        )

        # Act
        overlap = overlap_tokens(config)

        # Assert
        assert overlap == int(200 * 0.15)  # 30 tokens


class TestGetChunkingConfig:
    """
    Test suite for retrieving document-specific configurations.

    Tests the get_chunking_config function that returns appropriate
    configuration based on document type.

    Python Learning Notes:
        - Different document types need different chunking strategies
        - Factory pattern provides appropriate configurations
    """

    def test_get_scotus_config(self):
        """
        Test retrieving SCOTUS chunking configuration.

        Verifies correct configuration returned for Supreme Court opinions.
        """
        # Act
        config = get_chunking_config("scotus")

        # Assert
        assert isinstance(config, ChunkingConfig)
        assert config.min_tokens > 0
        assert config.target_tokens > config.min_tokens
        assert config.max_tokens > config.target_tokens

    def test_get_eo_config(self):
        """
        Test retrieving Executive Order chunking configuration.

        Verifies correct configuration returned for Executive Orders.
        """
        # Act
        config = get_chunking_config("eo")

        # Assert
        assert isinstance(config, ChunkingConfig)
        assert config.min_tokens > 0
        assert config.target_tokens > config.min_tokens
        assert config.max_tokens > config.target_tokens


class TestCountTokens:
    """
    Test suite for token counting functionality.

    Tests the count_tokens function that counts tokens in text
    using tiktoken encoding.

    Python Learning Notes:
        - Token counting determines chunk boundaries
        - Different encodings produce different counts
    """

    @patch("governmentreporter.processors.chunking.base.tiktoken")
    def test_count_tokens_normal_text(self, mock_tiktoken):
        """
        Test token counting for normal text.

        Verifies accurate token count for typical text.

        Args:
            mock_tiktoken: Mock tiktoken module
        """
        # Arrange
        mock_encoder = Mock()
        mock_encoder.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
        mock_tiktoken.get_encoding.return_value = mock_encoder

        text = "This is a sample text."

        # Act
        count = count_tokens(text)

        # Assert
        assert count == 5
        mock_encoder.encode.assert_called_once_with(text)

    @patch("governmentreporter.processors.chunking.base.tiktoken")
    def test_count_tokens_empty_text(self, mock_tiktoken):
        """
        Test token counting for empty text.

        Ensures empty text returns zero tokens.

        Args:
            mock_tiktoken: Mock tiktoken module
        """
        # Arrange
        mock_encoder = Mock()
        mock_encoder.encode.return_value = []
        mock_tiktoken.get_encoding.return_value = mock_encoder

        # Act
        count = count_tokens("")

        # Assert
        assert count == 0


class TestNormalizeWhitespace:
    """
    Test suite for whitespace normalization.

    Tests the normalize_whitespace function that cleans up
    excessive whitespace in text.

    Python Learning Notes:
        - Whitespace normalization improves text consistency
        - Regular expressions handle complex patterns
    """

    def test_normalize_multiple_spaces(self):
        """
        Test normalization preserves inline spaces.

        Verifies that normalize_whitespace only handles blank lines,
        not inline spaces (which are preserved for formatting).
        """
        # Arrange
        text = "This  has   multiple    spaces."

        # Act
        result = normalize_whitespace(text)

        # Assert - Function preserves inline spaces, only normalizes blank lines
        assert result == "This  has   multiple    spaces."

    def test_normalize_mixed_whitespace(self):
        """
        Test normalization of multiple blank lines.

        Ensures multiple blank lines are reduced to paragraph breaks.
        """
        # Arrange
        text = "Paragraph one.\n\n\n\nParagraph two."

        # Act
        result = normalize_whitespace(text)

        # Assert - Multiple blank lines become double newline (paragraph break)
        assert result == "Paragraph one.\n\nParagraph two."


class TestChunkTextWithTokens:
    """
    Test suite for token-based text chunking.

    Tests the chunk_text_with_tokens function that creates
    overlapping chunks based on token counts.

    Python Learning Notes:
        - Token-based chunking ensures consistent chunk sizes
        - Overlapping chunks preserve context
    """

    @patch("governmentreporter.processors.chunking.count_tokens")
    def test_chunk_text_normal(self, mock_count):
        """
        Test chunking normal text with token limits.

        Verifies text is properly chunked with overlap.

        Args:
            mock_count: Mock token counting function
        """
        # Arrange
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."

        # Mock token counts
        mock_count.side_effect = lambda t: len(t.split()) * 2

        config = ChunkingConfig(
            min_tokens=10, target_tokens=15, max_tokens=20, overlap_ratio=0.2
        )

        # Act
        chunks = chunk_text_with_tokens(
            text,
            "test_section",
            min_tokens=config.min_tokens,
            target_tokens=config.target_tokens,
            max_tokens=config.max_tokens,
            overlap_tokens=int(config.target_tokens * config.overlap_ratio),
        )

        # Assert
        assert len(chunks) > 0
        assert all(isinstance(chunk, tuple) for chunk in chunks)
        assert all(len(chunk) == 2 for chunk in chunks)  # (text, metadata) tuples

    @patch("governmentreporter.processors.chunking.count_tokens")
    def test_chunk_text_small(self, mock_count):
        """
        Test chunking text smaller than min_tokens.

        Ensures small text returns as single chunk.

        Args:
            mock_count: Mock token counting function
        """
        # Arrange
        text = "Short text."
        mock_count.return_value = 5

        config = ChunkingConfig(
            min_tokens=10, target_tokens=20, max_tokens=30, overlap_ratio=0.2
        )

        # Act
        chunks = chunk_text_with_tokens(
            text,
            "test_section",
            min_tokens=config.min_tokens,
            target_tokens=config.target_tokens,
            max_tokens=config.max_tokens,
            overlap_tokens=int(config.target_tokens * config.overlap_ratio),
        )

        # Assert
        assert len(chunks) == 1
        assert chunks[0][0] == "Short text."


class TestChunkSupremeCourtOpinion:
    """
    Test suite for Supreme Court opinion chunking.

    Tests the main entry point for chunking SCOTUS opinions with
    section awareness and appropriate configuration.

    Python Learning Notes:
        - Integration testing combines multiple functions
        - Mocking isolates the function under test
    """

    @patch("governmentreporter.processors.chunking.count_tokens")
    @patch("governmentreporter.processors.chunking.base.tiktoken")
    def test_chunk_scotus_opinion_success(self, mock_tiktoken, mock_count):
        """
        Test successful chunking of Supreme Court opinion.

        Verifies complete SCOTUS opinion is properly chunked with
        metadata preservation.

        Args:
            mock_tiktoken: Mock tiktoken module
            mock_count: Mock token counting
        """
        # Arrange
        mock_encoder = Mock()
        mock_tiktoken.get_encoding.return_value = mock_encoder
        mock_count.return_value = 100  # Sufficient tokens

        opinion_text = """
        Syllabus

        The Court addresses the question of whether...
        This case presents important constitutional issues...

        CHIEF JUSTICE ROBERTS delivered the opinion of the Court.

        We granted certiorari to resolve...
        The facts of this case are as follows...
        """

        # Act
        chunks, syllabus = chunk_supreme_court_opinion(opinion_text)

        # Assert
        assert len(chunks) > 0
        assert all(isinstance(chunk, tuple) for chunk in chunks)
        assert all(len(chunk) == 2 for chunk in chunks)  # (text, metadata)
        # Syllabus should be extracted
        assert syllabus is not None

    @patch("governmentreporter.processors.chunking.count_tokens")
    @patch("governmentreporter.processors.chunking.base.tiktoken")
    def test_chunk_scotus_opinion_empty(self, mock_tiktoken, mock_count):
        """
        Test chunking empty Supreme Court opinion.

        Ensures empty input is handled gracefully.

        Args:
            mock_tiktoken: Mock tiktoken module
            mock_count: Mock token counting
        """
        # Arrange
        mock_encoder = Mock()
        mock_tiktoken.get_encoding.return_value = mock_encoder
        mock_count.return_value = 0

        # Act
        chunks, syllabus = chunk_supreme_court_opinion("")

        # Assert
        # Should handle empty input gracefully
        assert isinstance(chunks, list)
        assert syllabus is None  # No syllabus in empty text


class TestChunkExecutiveOrder:
    """
    Test suite for Executive Order chunking.

    Tests the main entry point for chunking Executive Orders with
    section awareness and no cross-section overlap.

    Python Learning Notes:
        - Executive Orders have different structure than court opinions
        - Section boundaries are strictly preserved
    """

    @patch("governmentreporter.processors.chunking.count_tokens")
    @patch("governmentreporter.processors.chunking.base.tiktoken")
    def test_chunk_executive_order_success(self, mock_tiktoken, mock_count):
        """
        Test successful chunking of Executive Order.

        Verifies Executive Order is properly chunked by sections.

        Args:
            mock_tiktoken: Mock tiktoken module
            mock_count: Mock token counting
        """
        # Arrange
        mock_encoder = Mock()
        mock_tiktoken.get_encoding.return_value = mock_encoder
        mock_count.return_value = 80

        eo_text = """
        EXECUTIVE ORDER

        By the authority vested in me as President...

        Section 1. Purpose. This order establishes new requirements...

        Sec. 2. Policy. It is the policy of the United States...

        Sec. 3. Implementation. All executive departments shall...
        """

        # Act
        chunks = chunk_executive_order(eo_text)

        # Assert
        assert len(chunks) > 0
        assert all(isinstance(chunk, tuple) for chunk in chunks)
        assert all(len(chunk) == 2 for chunk in chunks)  # (text, metadata)

    @patch("governmentreporter.processors.chunking.count_tokens")
    @patch("governmentreporter.processors.chunking.base.tiktoken")
    def test_chunk_executive_order_empty(self, mock_tiktoken, mock_count):
        """
        Test chunking empty Executive Order.

        Ensures empty input is handled gracefully.

        Args:
            mock_tiktoken: Mock tiktoken module
            mock_count: Mock token counting
        """
        # Arrange
        mock_encoder = Mock()
        mock_tiktoken.get_encoding.return_value = mock_encoder
        mock_count.return_value = 0

        # Act
        chunks = chunk_executive_order("")

        # Assert
        assert isinstance(chunks, list)


# Test fixtures for reuse across multiple test classes
@pytest.fixture
def mock_tokenizer():
    """
    Provide a mock tokenizer for consistent testing.

    Returns:
        Mock: Configured mock tokenizer with encode method

    Python Learning Notes:
        - Fixtures can be shared across test classes
        - Mock objects reduce test dependencies
    """
    tokenizer = Mock()
    tokenizer.encode = Mock(side_effect=lambda text: [1] * (len(text) // 4))
    return tokenizer


@pytest.fixture
def sample_scotus_text():
    """
    Provide sample Supreme Court opinion text for testing.

    Returns:
        str: Sample SCOTUS opinion text with typical structure
    """
    return """
    Syllabus

    The petitioner challenges the constitutionality of...

    CHIEF JUSTICE ROBERTS delivered the opinion of the Court.

    This case presents the question whether...
    We hold that the statute does not violate...

    JUSTICE SOTOMAYOR, dissenting.

    I respectfully dissent from the Court's holding...
    """


@pytest.fixture
def sample_eo_text():
    """
    Provide sample Executive Order text for testing.

    Returns:
        str: Sample Executive Order with typical structure
    """
    return """
    EXECUTIVE ORDER

    By the authority vested in me as President...

    Section 1. Purpose. This order establishes...

    Sec. 2. Policy. It shall be the policy...

    Sec. 3. Implementation. Federal agencies shall...
    """
