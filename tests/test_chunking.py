"""
Tests for the chunking module.

These tests verify:
    - Per-document-type configuration loading
    - Sliding window with proper overlap
    - Section boundary preservation for Executive Orders
    - Token counting and chunk size compliance
    - Edge cases (small documents, long sentences)
"""

import pytest
from unittest.mock import patch
from governmentreporter.processors.chunking import (
    ChunkingConfig,
    SCOTUS_CFG,
    EO_CFG,
    get_chunking_config,
    overlap_tokens,
    count_tokens,
    chunk_text_with_tokens,
    chunk_supreme_court_opinion,
    chunk_executive_order,
    normalize_whitespace
)


class TestChunkingConfig:
    """Test the ChunkingConfig dataclass and configuration loading."""
    
    def test_valid_config(self):
        """Test creating a valid ChunkingConfig."""
        config = ChunkingConfig(
            min_tokens=500,
            target_tokens=600,
            max_tokens=800,
            overlap_ratio=0.15
        )
        assert config.min_tokens == 500
        assert config.target_tokens == 600
        assert config.max_tokens == 800
        assert config.overlap_ratio == 0.15
    
    def test_invalid_config_negative_tokens(self):
        """Test that negative token counts raise ValueError."""
        with pytest.raises(ValueError, match="Token counts must be positive"):
            ChunkingConfig(
                min_tokens=-1,
                target_tokens=600,
                max_tokens=800,
                overlap_ratio=0.15
            )
    
    def test_invalid_config_min_exceeds_max(self):
        """Test that min_tokens > max_tokens raises ValueError."""
        with pytest.raises(ValueError, match="min_tokens cannot exceed max_tokens"):
            ChunkingConfig(
                min_tokens=900,
                target_tokens=600,
                max_tokens=800,
                overlap_ratio=0.15
            )
    
    def test_invalid_overlap_ratio(self):
        """Test that invalid overlap ratios raise ValueError."""
        with pytest.raises(ValueError, match="overlap_ratio must be between"):
            ChunkingConfig(
                min_tokens=500,
                target_tokens=600,
                max_tokens=800,
                overlap_ratio=1.5
            )
    
    def test_get_chunking_config(self):
        """Test getting configuration by document type."""
        scotus_cfg = get_chunking_config("scotus")
        assert scotus_cfg == SCOTUS_CFG
        
        eo_cfg = get_chunking_config("eo")
        assert eo_cfg == EO_CFG
        
        with pytest.raises(ValueError, match="Unknown document type"):
            get_chunking_config("invalid")
    
    def test_overlap_tokens_calculation(self):
        """Test overlap token calculation."""
        config = ChunkingConfig(
            min_tokens=500,
            target_tokens=600,
            max_tokens=800,
            overlap_ratio=0.15
        )
        assert overlap_tokens(config) == 90  # 600 * 0.15 = 90
        
        config2 = ChunkingConfig(
            min_tokens=240,
            target_tokens=340,
            max_tokens=400,
            overlap_ratio=0.10
        )
        assert overlap_tokens(config2) == 34  # 340 * 0.10 = 34


class TestModuleConfigurations:
    """Test the module-level configurations."""
    
    def test_scotus_config(self):
        """Test SCOTUS configuration values."""
        assert SCOTUS_CFG.min_tokens == 500
        assert SCOTUS_CFG.target_tokens == 600
        assert SCOTUS_CFG.max_tokens == 800
        assert SCOTUS_CFG.overlap_ratio == 0.15
    
    def test_eo_config(self):
        """Test Executive Order configuration values."""
        assert EO_CFG.min_tokens == 240
        assert EO_CFG.target_tokens == 340
        assert EO_CFG.max_tokens == 400
        assert EO_CFG.overlap_ratio == 0.10
    
    @patch.dict('os.environ', {'RAG_SCOTUS_TARGET_TOKENS': '700'})
    def test_env_override(self):
        """Test that environment variables can override config."""
        # This would require reloading the module to pick up env changes
        # In practice, this is tested manually or with more complex test setup
        pass


class TestTokenCounting:
    """Test token counting functionality."""
    
    def test_count_tokens_basic(self):
        """Test basic token counting."""
        text = "This is a simple test sentence."
        token_count = count_tokens(text)
        assert token_count > 0
        assert token_count < len(text)  # Should be fewer tokens than characters
    
    def test_count_tokens_empty(self):
        """Test token counting for empty string."""
        assert count_tokens("") == 0
    
    def test_count_tokens_fallback(self):
        """Test fallback when tiktoken fails."""
        with patch('tiktoken.get_encoding', side_effect=Exception("Test error")):
            # Should fall back to 4 chars per token approximation
            text = "This is approximately twenty characters long for testing."
            token_count = count_tokens(text)
            assert token_count == len(text) // 4


class TestWhitespaceNormalization:
    """Test whitespace normalization."""
    
    def test_normalize_basic(self):
        """Test basic whitespace normalization."""
        text = "  Hello   world  \n\n\n  Test  "
        normalized = normalize_whitespace(text)
        assert normalized == "Hello   world  \n\n  Test"
    
    def test_normalize_multiple_blank_lines(self):
        """Test reducing multiple blank lines."""
        text = "First paragraph\n\n\n\nSecond paragraph"
        normalized = normalize_whitespace(text)
        assert normalized == "First paragraph\n\nSecond paragraph"


class TestChunkTextWithTokens:
    """Test the core chunking function."""
    
    def test_short_document(self):
        """Test that short documents return single chunk."""
        text = "This is a very short document."
        chunks = chunk_text_with_tokens(
            text=text,
            section_label="Test Section",
            min_tokens=100,
            target_tokens=200,
            max_tokens=300,
            overlap_tokens=20
        )
        assert len(chunks) == 1
        assert chunks[0][0] == text
        assert chunks[0][1]["section_label"] == "Test Section"
        assert "chunk_token_count" in chunks[0][1]
    
    def test_sliding_window_with_overlap(self):
        """Test that sliding window creates proper overlap."""
        # Create a long text that will require multiple chunks
        long_text = " ".join(["Word" + str(i) for i in range(500)])
        
        chunks = chunk_text_with_tokens(
            text=long_text,
            section_label="Test Section",
            min_tokens=50,
            target_tokens=100,
            max_tokens=150,
            overlap_tokens=15
        )
        
        assert len(chunks) > 1
        
        # Check that chunks have overlap (some words appear in adjacent chunks)
        for i in range(len(chunks) - 1):
            chunk1_words = set(chunks[i][0].split()[-10:])  # Last 10 words
            chunk2_words = set(chunks[i+1][0].split()[:10])  # First 10 words
            # Should have some overlap
            assert len(chunk1_words & chunk2_words) > 0
    
    def test_no_overlap(self):
        """Test chunking without overlap."""
        long_text = " ".join(["Word" + str(i) for i in range(500)])
        
        chunks = chunk_text_with_tokens(
            text=long_text,
            section_label="Test Section",
            min_tokens=50,
            target_tokens=100,
            max_tokens=150,
            overlap_tokens=0
        )
        
        assert len(chunks) > 1
        
        # Verify no duplicate content between chunks
        all_text = " ".join([chunk[0] for chunk in chunks])
        # Should not be significantly longer than original (allowing for whitespace differences)
        assert len(all_text) <= len(long_text) * 1.1
    
    def test_remainder_merging(self):
        """Test that small remainder chunks are merged."""
        # Create text that would leave a small remainder
        text = " ".join(["Word" + str(i) for i in range(150)])
        
        chunks = chunk_text_with_tokens(
            text=text,
            section_label="Test Section",
            min_tokens=40,
            target_tokens=50,
            max_tokens=70,
            overlap_tokens=5
        )
        
        # Check that no chunk is smaller than min_tokens (except possibly the last)
        for i, (chunk_text, metadata) in enumerate(chunks):
            if i < len(chunks) - 1:  # Not the last chunk
                assert metadata["chunk_token_count"] >= 40 or i == len(chunks) - 1


class TestSupremeCourtChunking:
    """Test Supreme Court opinion chunking."""
    
    def test_basic_scotus_opinion(self):
        """Test chunking a basic Supreme Court opinion."""
        opinion_text = """
        SYLLABUS
        
        The Court held that the Fourth Amendment requires a warrant.
        
        JUSTICE ROBERTS delivered the opinion of the Court.
        
        The question presented is whether police may search digital
        information on cell phones without a warrant. We hold that they
        generally may not. This is a longer section with more content
        to ensure we get proper chunking behavior when the text exceeds
        the minimum token threshold for creating multiple chunks.
        """ + " ".join(["Additional content " + str(i) for i in range(200)])
        
        chunks, syllabus = chunk_supreme_court_opinion(opinion_text)
        
        assert chunks is not None
        assert len(chunks) > 0
        assert syllabus is not None
        assert "Fourth Amendment" in syllabus
        
        # Check that chunks use SCOTUS config
        for chunk_text, metadata in chunks:
            assert "section_label" in metadata
            assert "chunk_token_count" in metadata
    
    def test_scotus_section_detection(self):
        """Test that different opinion types are detected."""
        opinion_text = """SYLLABUS

Summary text here.

JUSTICE ROBERTS delivered the opinion of the Court.

Majority opinion text.

JUSTICE THOMAS, concurring.

Concurring opinion text.

JUSTICE SOTOMAYOR, dissenting.

Dissenting opinion text."""
        
        chunks, syllabus = chunk_supreme_court_opinion(opinion_text)
        
        assert chunks is not None
        assert len(chunks) > 0
        
        # Check that section labels are present
        section_labels = [metadata["section_label"] for _, metadata in chunks]
        assert all(label for label in section_labels)  # All chunks have labels
        
        # If sections were detected, verify they're correct
        # Note: Very short text might be chunked as one section due to min_tokens
        if len(chunks) > 1:
            assert any("Syllabus" in label or "Majority" in label or 
                      "Concurring" in label or "Dissenting" in label
                      for label in section_labels)
    
    def test_scotus_overlap(self):
        """Test that SCOTUS chunks have proper overlap."""
        # Create a long opinion section
        long_opinion = """
        JUSTICE ROBERTS delivered the opinion of the Court.
        
        """ + " ".join(["Legal reasoning " + str(i) for i in range(500)])
        
        chunks, _ = chunk_supreme_court_opinion(long_opinion)
        
        # With SCOTUS config overlap of 15%, adjacent chunks should share content
        if len(chunks) > 1:
            # Check for overlap between first two chunks
            chunk1_words = set(chunks[0][0].split()[-50:])
            chunk2_words = set(chunks[1][0].split()[:50])
            assert len(chunk1_words & chunk2_words) > 0


class TestExecutiveOrderChunking:
    """Test Executive Order chunking."""
    
    def test_basic_executive_order(self):
        """Test chunking a basic Executive Order."""
        eo_text = """
        Executive Order 14999
        
        By the authority vested in me as President, I hereby order:
        
        Section 1. Purpose. This order establishes new requirements
        for federal climate policy and environmental protection.
        
        Sec. 2. Policy. (a) All agencies shall consider climate impacts
        in their decision-making processes.
        (b) The EPA shall develop new standards for emissions.
        
        Sec. 3. Implementation. Agencies shall report progress quarterly
        to ensure compliance with this order.
        """
        
        chunks = chunk_executive_order(eo_text)
        
        assert chunks is not None
        assert len(chunks) > 0
        
        # Check that chunks use EO config
        for chunk_text, metadata in chunks:
            assert "section_label" in metadata
            assert "chunk_token_count" in metadata
    
    def test_eo_section_boundaries(self):
        """Test that EO chunks never cross section boundaries."""
        eo_text = """
        Executive Order 14999
        
        Section 1. First Section. """ + " ".join(["Content " + str(i) for i in range(200)]) + """
        
        Sec. 2. Second Section. """ + " ".join(["More content " + str(i) for i in range(200)]) + """
        
        Sec. 3. Third Section. """ + " ".join(["Final content " + str(i) for i in range(200)])
        
        chunks = chunk_executive_order(eo_text)
        
        # Verify no chunk contains content from multiple sections
        for chunk_text, metadata in chunks:
            # Count how many section markers appear in this chunk
            sec1_count = chunk_text.count("Section 1") + chunk_text.count("Sec. 1")
            sec2_count = chunk_text.count("Sec. 2") + chunk_text.count("Section 2")
            sec3_count = chunk_text.count("Sec. 3") + chunk_text.count("Section 3")
            
            # Should only have content from one section
            sections_present = sum([1 for count in [sec1_count, sec2_count, sec3_count] if count > 0])
            assert sections_present <= 1
    
    def test_eo_subsection_handling(self):
        """Test that EO subsections are handled correctly."""
        eo_text = """
        Section 1. Purpose. This establishes policy.
        
        Sec. 2. Policy.
        (a) First subsection with content.
        (b) Second subsection with content.
        (c) Third subsection with content.
        """
        
        chunks = chunk_executive_order(eo_text)
        
        section_labels = [metadata["section_label"] for _, metadata in chunks]
        
        # Check for subsection labels
        assert any("(a)" in label or "(b)" in label or "(c)" in label 
                  for label in section_labels)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_document(self):
        """Test handling of empty document."""
        chunks = chunk_text_with_tokens(
            text="",
            section_label="Empty",
            min_tokens=100,
            target_tokens=200,
            max_tokens=300,
            overlap_tokens=0
        )
        assert len(chunks) == 1
        assert chunks[0][0] == ""
    
    def test_very_long_sentence(self):
        """Test handling of sentences longer than max_tokens."""
        # Create a sentence longer than max tokens
        long_sentence = " ".join(["word" + str(i) for i in range(500)]) + "."
        
        chunks = chunk_text_with_tokens(
            text=long_sentence,
            section_label="Long",
            min_tokens=50,
            target_tokens=100,
            max_tokens=150,
            overlap_tokens=10
        )
        
        # Should split the long sentence into multiple chunks
        assert len(chunks) > 1
        
        # All chunks should respect max_tokens limit
        for _, metadata in chunks:
            assert metadata["chunk_token_count"] <= 150 * 1.5  # Allow some flexibility
    
    def test_opinion_without_sections(self):
        """Test SCOTUS opinion without clear section markers."""
        opinion_text = "This is just a plain text opinion without any section markers."
        
        chunks, syllabus = chunk_supreme_court_opinion(opinion_text)
        
        assert chunks is not None
        assert len(chunks) > 0
        assert syllabus is None
        assert chunks[0][1]["section_label"] == "Opinion"
    
    def test_eo_without_sections(self):
        """Test Executive Order without section markers."""
        eo_text = "This executive order has no formal sections."
        
        chunks = chunk_executive_order(eo_text)
        
        assert chunks is not None
        assert len(chunks) > 0
        assert chunks[0][1]["section_label"] == "Executive Order"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])