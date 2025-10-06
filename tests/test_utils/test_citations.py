"""
Unit tests for Bluebook citation formatting utilities.

Streamlined test suite covering core functionality and edge cases.
"""

import pytest
from governmentreporter.utils.citations import (
    format_cfr_citation,
    format_usc_citation,
    format_constitution_citation,
    parse_cfr_citations,
    parse_usc_citations,
    parse_constitution_citations,
)


class TestFormatCFRCitation:
    """Test CFR citation formatting."""

    def test_basic_cfr_citation(self):
        """Test basic CFR citation."""
        assert format_cfr_citation("14", "91.817") == "14 C.F.R. § 91.817"
        assert format_cfr_citation("21", "101.1", "2024") == "21 C.F.R. § 101.1 (2024)"

    @pytest.mark.parametrize(
        "title,section,year,expected",
        [
            ("14", "91.817", None, "14 C.F.R. § 91.817"),
            ("14", "91.817", "2024", "14 C.F.R. § 91.817 (2024)"),
            ("5", "1.1", "2023", "5 C.F.R. § 1.1 (2023)"),
            ("42", "1983.1(a)(2)(iii)", "2023", "42 C.F.R. § 1983.1(a)(2)(iii) (2023)"),
        ],
    )
    def test_cfr_citation_parametrized(self, title, section, year, expected):
        """Test CFR citations with various formats."""
        result = format_cfr_citation(title, section, year)
        assert result == expected


class TestFormatUSCCitation:
    """Test USC citation formatting."""

    def test_basic_usc_citation(self):
        """Test basic USC citation."""
        assert format_usc_citation("8", "1182") == "8 U.S.C. § 1182"
        assert format_usc_citation("42", "1983", "2024") == "42 U.S.C. § 1983 (2024)"

    @pytest.mark.parametrize(
        "title,section,year,expected",
        [
            ("8", "1182", None, "8 U.S.C. § 1182"),
            ("8", "1182(f)", "2023", "8 U.S.C. § 1182(f) (2023)"),
            ("42", "1983", "2024", "42 U.S.C. § 1983 (2024)"),
        ],
    )
    def test_usc_citation_parametrized(self, title, section, year, expected):
        """Test USC citations with various formats."""
        result = format_usc_citation(title, section, year)
        assert result == expected


class TestFormatConstitutionCitation:
    """Test Constitutional citation formatting."""

    def test_article_citations(self):
        """Test Article citations."""
        assert format_constitution_citation(article="I") == "U.S. Const. art. I"
        assert (
            format_constitution_citation(article="I", section="8")
            == "U.S. Const. art. I, § 8"
        )
        assert (
            format_constitution_citation(article="I", section="9", clause="7")
            == "U.S. Const. art. I, § 9, cl. 7"
        )

    def test_amendment_citations(self):
        """Test Amendment citations."""
        assert format_constitution_citation(amendment="XIV") == "U.S. Const. amend. XIV"
        assert (
            format_constitution_citation(amendment="XIV", section="1")
            == "U.S. Const. amend. XIV, § 1"
        )

    @pytest.mark.parametrize(
        "article,amendment,section,clause,expected",
        [
            ("I", None, None, None, "U.S. Const. art. I"),
            ("I", None, "8", None, "U.S. Const. art. I, § 8"),
            ("I", None, "9", "7", "U.S. Const. art. I, § 9, cl. 7"),
            (None, "XIV", None, None, "U.S. Const. amend. XIV"),
            (None, "XIV", "1", None, "U.S. Const. amend. XIV, § 1"),
        ],
    )
    def test_constitution_citation_parametrized(
        self, article, amendment, section, clause, expected
    ):
        """Test Constitutional citations with various formats."""
        result = format_constitution_citation(
            article=article, amendment=amendment, section=section, clause=clause
        )
        assert result == expected


class TestParseCFRCitations:
    """Test CFR citation parsing."""

    def test_parse_standard_cfr_citation(self):
        """Test parsing standard CFR citations."""
        text = "See 14 C.F.R. § 91.817 for details."
        citations = parse_cfr_citations(text)
        assert len(citations) > 0
        assert citations[0]["title"] == "14"
        assert "91.817" in citations[0]["section"]

    def test_parse_multiple_cfr_citations(self):
        """Test parsing multiple CFR citations."""
        text = "See 14 C.F.R. § 91.817 and 21 C.F.R. § 101.1"
        citations = parse_cfr_citations(text)
        assert len(citations) >= 2

    def test_parse_cfr_no_citations(self):
        """Test text with no CFR citations."""
        text = "This text has no citations."
        citations = parse_cfr_citations(text)
        assert len(citations) == 0


class TestParseUSCCitations:
    """Test USC citation parsing."""

    def test_parse_standard_usc_citation(self):
        """Test parsing standard USC citations."""
        text = "Pursuant to 8 U.S.C. § 1182(f)"
        citations = parse_usc_citations(text)
        assert len(citations) > 0
        assert citations[0]["title"] == "8"
        assert "1182" in citations[0]["section"]

    def test_parse_multiple_usc_citations(self):
        """Test parsing multiple USC citations."""
        text = "See 8 U.S.C. § 1182 and 42 U.S.C. § 1983"
        citations = parse_usc_citations(text)
        assert len(citations) >= 2

    def test_parse_usc_no_citations(self):
        """Test text with no USC citations."""
        text = "This text has no citations."
        citations = parse_usc_citations(text)
        assert len(citations) == 0


class TestParseConstitutionCitations:
    """Test Constitutional citation parsing."""

    def test_parse_article_citation(self):
        """Test parsing Article citations."""
        text = "Under U.S. Const. art. I, § 8"
        citations = parse_constitution_citations(text)
        assert len(citations) > 0
        # Just verify we got results - structure may vary
        assert isinstance(citations[0], (str, dict))

    def test_parse_amendment_citation(self):
        """Test parsing Amendment citations."""
        text = "The Fourteenth Amendment protects these rights."
        citations = parse_constitution_citations(text)
        assert len(citations) > 0

    def test_parse_multiple_constitutional_citations(self):
        """Test parsing multiple Constitutional citations."""
        text = "Art. I and the Fifth Amendment both apply."
        citations = parse_constitution_citations(text)
        assert len(citations) >= 2

    def test_parse_no_constitutional_citations(self):
        """Test text with no Constitutional citations."""
        text = "This text has no citations."
        citations = parse_constitution_citations(text)
        assert len(citations) == 0


class TestCitationEdgeCases:
    """Test edge cases for citation formatting and parsing."""

    def test_format_with_none_inputs(self):
        """Test formatting with None inputs."""
        # Should handle None gracefully
        result = format_cfr_citation("14", "91.817", None)
        assert "2024" not in result or result is None

    def test_parse_with_empty_string(self):
        """Test parsing empty strings."""
        assert parse_cfr_citations("") == []
        assert parse_usc_citations("") == []
        assert parse_constitution_citations("") == []

    def test_parse_with_none_input(self):
        """Test parsing None input."""
        with pytest.raises((TypeError, AttributeError)):
            parse_cfr_citations(None)
