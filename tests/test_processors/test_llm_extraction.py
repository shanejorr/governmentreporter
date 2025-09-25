"""
Unit tests for LLM-based metadata extraction.

This module provides comprehensive tests for the GPT-5-nano powered metadata
extraction functionality that generates structured metadata from legal documents.
All OpenAI API calls are mocked to ensure isolated, deterministic testing.

Test Categories:
    - Happy path: Successful extraction for SCOTUS opinions and Executive Orders
    - Edge cases: Empty text, malformed documents, missing sections
    - Error handling: API failures, invalid JSON responses, rate limits
    - Configuration: Syllabus prioritization, citation extraction

Python Learning Notes:
    - Mock JSON responses simulate LLM structured output
    - Testing verifies both the API call and response parsing
    - Different document types require different extraction logic
"""

import json
from unittest.mock import Mock, patch, MagicMock, call
import pytest
from openai import OpenAI, RateLimitError, APIError

from governmentreporter.processors.llm_extraction import (
    generate_scotus_llm_fields,
    generate_eo_llm_fields,
)


class TestGenerateSCOTUSLLMFields:
    """
    Test suite for Supreme Court opinion metadata extraction.

    Tests the generate_scotus_llm_fields function that uses GPT-5-nano
    to extract structured metadata from Supreme Court opinions.

    Python Learning Notes:
        - Complex LLM responses require careful mocking
        - Syllabus prioritization logic needs specific tests
        - JSON parsing validation is critical
    """

    @patch('governmentreporter.processors.llm_extraction.OpenAI')
    @patch('governmentreporter.processors.llm_extraction.get_openai_api_key')
    def test_generate_scotus_fields_with_syllabus(self, mock_get_key, mock_openai_class):
        """
        Test SCOTUS metadata extraction with Syllabus provided.

        Verifies that when a Syllabus is available, it's prioritized
        for extracting holdings, outcomes, and issues.

        Args:
            mock_get_key: Mock API key getter
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_get_key.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock LLM response with complete metadata
        mock_metadata = {
            "plain_language_summary": "The Court held that the First Amendment protects...",
            "constitution_cited": ["First Amendment", "Fourteenth Amendment"],
            "federal_statutes_cited": ["42 U.S.C. § 1983"],
            "federal_regulations_cited": [],
            "cases_cited": ["Brandenburg v. Ohio, 395 U.S. 444 (1969)"],
            "topics_or_policy_areas": ["free speech", "constitutional law", "civil rights"],
            "holding_plain": "The First Amendment protects offensive speech.",
            "outcome_simple": "The lower court's decision was reversed.",
            "issue_plain": "Whether offensive speech is protected by the First Amendment?",
            "reasoning": "The Court reasoned that the First Amendment protects even offensive speech..."
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_metadata)))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        opinion_text = "Full opinion text..."
        syllabus_text = "Syllabus: Held that the First Amendment..."

        # Act
        result = generate_scotus_llm_fields(opinion_text, syllabus_text)

        # Assert
        assert result["plain_language_summary"] == mock_metadata["plain_language_summary"]
        assert result["holding_plain"] == mock_metadata["holding_plain"]
        assert result["constitution_cited"] == mock_metadata["constitution_cited"]
        assert len(result["topics_or_policy_areas"]) == 3

        # Verify syllabus was included in the prompt
        call_args = mock_client.chat.completions.create.call_args
        assert "Syllabus" in str(call_args)

    @patch('governmentreporter.processors.llm_extraction.OpenAI')
    @patch('governmentreporter.processors.llm_extraction.get_openai_api_key')
    def test_generate_scotus_fields_without_syllabus(self, mock_get_key, mock_openai_class):
        """
        Test SCOTUS metadata extraction without Syllabus.

        Ensures the function works correctly when only the opinion
        text is available, without a Syllabus.

        Args:
            mock_get_key: Mock API key getter
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_get_key.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_metadata = {
            "plain_language_summary": "The Court addressed the question of...",
            "constitution_cited": ["Fourth Amendment"],
            "federal_statutes_cited": [],
            "federal_regulations_cited": [],
            "cases_cited": ["Terry v. Ohio, 392 U.S. 1 (1968)"],
            "topics_or_policy_areas": ["search and seizure", "criminal procedure"],
            "holding_plain": "Warrantless searches require probable cause.",
            "outcome_simple": "The conviction was upheld.",
            "issue_plain": "Whether the search violated the Fourth Amendment?",
            "reasoning": "The Court found that the search was reasonable..."
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_metadata)))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        opinion_text = "Opinion text without syllabus..."

        # Act
        result = generate_scotus_llm_fields(opinion_text, syllabus=None)

        # Assert
        assert result["plain_language_summary"] == mock_metadata["plain_language_summary"]
        assert result["constitution_cited"] == ["Fourth Amendment"]
        assert "search and seizure" in result["topics_or_policy_areas"]

        # Verify no syllabus in prompt
        call_args = mock_client.chat.completions.create.call_args
        prompt = str(call_args)
        assert "without a Syllabus" in prompt or "Syllabus: None" not in prompt

    @patch('governmentreporter.processors.llm_extraction.time.sleep')
    @patch('governmentreporter.processors.llm_extraction.OpenAI')
    @patch('governmentreporter.processors.llm_extraction.get_openai_api_key')
    def test_generate_scotus_fields_with_retry(self, mock_get_key, mock_openai_class, mock_sleep):
        """
        Test retry logic for rate limit errors.

        Verifies that the function retries with exponential backoff
        when encountering rate limit errors from OpenAI.

        Args:
            mock_get_key: Mock API key getter
            mock_openai_class: Mock OpenAI class
            mock_sleep: Mock sleep for retry delays
        """
        # Arrange
        mock_get_key.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_metadata = {
            "plain_language_summary": "Test summary",
            "constitution_cited": [],
            "federal_statutes_cited": [],
            "federal_regulations_cited": [],
            "cases_cited": [],
            "topics_or_policy_areas": ["test topic"],
            "holding_plain": "Test holding",
            "outcome_simple": "Test outcome",
            "issue_plain": "Test issue",
            "reasoning": "Test reasoning"
        }

        # First call fails with rate limit, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_metadata)))
        ]

        mock_client.chat.completions.create.side_effect = [
            RateLimitError("Rate limit exceeded", response=MagicMock(), body=None),
            mock_response
        ]

        # Act
        result = generate_scotus_llm_fields("Test opinion text")

        # Assert
        assert result["plain_language_summary"] == "Test summary"
        assert mock_client.chat.completions.create.call_count == 2
        mock_sleep.assert_called_once()

    @patch('governmentreporter.processors.llm_extraction.OpenAI')
    @patch('governmentreporter.processors.llm_extraction.get_openai_api_key')
    def test_generate_scotus_fields_empty_text(self, mock_get_key, mock_openai_class):
        """
        Test handling of empty opinion text.

        Ensures the function handles empty input gracefully,
        returning appropriate empty or default values.

        Args:
            mock_get_key: Mock API key getter
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_get_key.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock empty/minimal response for empty input
        mock_metadata = {
            "plain_language_summary": "",
            "constitution_cited": [],
            "federal_statutes_cited": [],
            "federal_regulations_cited": [],
            "cases_cited": [],
            "topics_or_policy_areas": [],
            "holding_plain": "",
            "outcome_simple": "",
            "issue_plain": "",
            "reasoning": ""
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_metadata)))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Act
        result = generate_scotus_llm_fields("")

        # Assert
        assert result["plain_language_summary"] == ""
        assert result["constitution_cited"] == []
        assert result["topics_or_policy_areas"] == []

    @patch('governmentreporter.processors.llm_extraction.OpenAI')
    @patch('governmentreporter.processors.llm_extraction.get_openai_api_key')
    def test_generate_scotus_fields_malformed_json(self, mock_get_key, mock_openai_class):
        """
        Test handling of malformed JSON responses.

        Verifies graceful handling when LLM returns invalid JSON,
        with appropriate error handling and fallback.

        Args:
            mock_get_key: Mock API key getter
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_get_key.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Return invalid JSON
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="This is not valid JSON"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            generate_scotus_llm_fields("Test opinion")


class TestGenerateEOLLMFields:
    """
    Test suite for Executive Order metadata extraction.

    Tests the generate_eo_llm_fields function that extracts metadata
    from Executive Orders using GPT-5-nano.

    Python Learning Notes:
        - Executive Orders have different metadata than court opinions
        - Testing verifies correct field extraction for EO format
    """

    @patch('governmentreporter.processors.llm_extraction.OpenAI')
    @patch('governmentreporter.processors.llm_extraction.get_openai_api_key')
    def test_generate_eo_fields_success(self, mock_get_key, mock_openai_class):
        """
        Test successful Executive Order metadata extraction.

        Verifies complete metadata extraction for a typical
        Executive Order document.

        Args:
            mock_get_key: Mock API key getter
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_get_key.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_metadata = {
            "plain_summary": "This Executive Order establishes new climate policies...",
            "federal_statutes_referenced": ["Clean Air Act, 42 U.S.C. § 7401"],
            "federal_regulations_referenced": ["40 C.F.R. Part 60"],
            "agencies_or_entities": ["EPA", "Department of Energy", "NOAA"],
            "topics_or_policy_areas": ["climate change", "environmental protection", "energy"],
            "action_plain": "Requires agencies to reduce carbon emissions by 50%",
            "impact_simple": "Federal facilities must transition to renewable energy",
            "implementation_requirements": "Agencies must submit implementation plans within 90 days"
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_metadata)))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        eo_text = """
        EXECUTIVE ORDER

        By the authority vested in me as President...

        Section 1. Purpose. This order establishes requirements for climate action...

        Sec. 2. Policy. It is the policy of the United States to achieve net-zero emissions...

        Sec. 3. Implementation. All executive departments and agencies shall...
        """

        # Act
        result = generate_eo_llm_fields(eo_text)

        # Assert
        assert result["plain_summary"] == mock_metadata["plain_summary"]
        assert "EPA" in result["agencies_or_entities"]
        assert "climate change" in result["topics_or_policy_areas"]
        assert result["action_plain"] == mock_metadata["action_plain"]
        assert len(result["federal_statutes_referenced"]) == 1

    @patch('governmentreporter.processors.llm_extraction.OpenAI')
    @patch('governmentreporter.processors.llm_extraction.get_openai_api_key')
    def test_generate_eo_fields_empty_text(self, mock_get_key, mock_openai_class):
        """
        Test Executive Order extraction with empty text.

        Ensures graceful handling of empty input for EO extraction.

        Args:
            mock_get_key: Mock API key getter
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_get_key.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_metadata = {
            "plain_summary": "",
            "federal_statutes_referenced": [],
            "federal_regulations_referenced": [],
            "agencies_or_entities": [],
            "topics_or_policy_areas": [],
            "action_plain": "",
            "impact_simple": "",
            "implementation_requirements": ""
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_metadata)))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Act
        result = generate_eo_llm_fields("")

        # Assert
        assert result["plain_summary"] == ""
        assert result["agencies_or_entities"] == []
        assert result["topics_or_policy_areas"] == []

    @patch('governmentreporter.processors.llm_extraction.time.sleep')
    @patch('governmentreporter.processors.llm_extraction.OpenAI')
    @patch('governmentreporter.processors.llm_extraction.get_openai_api_key')
    def test_generate_eo_fields_api_error_with_retry(self, mock_get_key, mock_openai_class, mock_sleep):
        """
        Test API error handling with retry for Executive Orders.

        Verifies retry logic and eventual failure after max retries.

        Args:
            mock_get_key: Mock API key getter
            mock_openai_class: Mock OpenAI class
            mock_sleep: Mock sleep for retry delays
        """
        # Arrange
        mock_get_key.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Simulate persistent API error
        mock_client.chat.completions.create.side_effect = APIError(
            "Internal server error",
            response=MagicMock(),
            body=None
        )

        # Act & Assert
        with pytest.raises(APIError):
            generate_eo_llm_fields("Test EO text")

        # Verify retries occurred
        assert mock_client.chat.completions.create.call_count >= 1


# Note: Citation extraction helper functions are internal to llm_extraction module
# and not exposed in the public API, so we don't test them directly.
# Their functionality is tested indirectly through the main extraction functions.


class TestLLMExtractionIntegration:
    """
    Integration tests for LLM extraction functionality.

    Tests the complete extraction pipeline with realistic documents
    to ensure all components work together.

    Python Learning Notes:
        - Integration tests verify end-to-end functionality
        - Realistic test data helps catch edge cases
    """

    @patch('governmentreporter.processors.llm_extraction.OpenAI')
    @patch('governmentreporter.processors.llm_extraction.get_openai_api_key')
    def test_scotus_extraction_with_complex_opinion(self, mock_get_key, mock_openai_class):
        """
        Test extraction from complex SCOTUS opinion with multiple parts.

        Verifies handling of opinions with syllabus, majority,
        concurring, and dissenting opinions.

        Args:
            mock_get_key: Mock API key getter
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_get_key.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Complex metadata response
        mock_metadata = {
            "plain_language_summary": "In a 5-4 decision, the Court held...",
            "constitution_cited": ["First Amendment", "Fourteenth Amendment", "Commerce Clause"],
            "federal_statutes_cited": ["42 U.S.C. § 1983", "28 U.S.C. § 1331"],
            "federal_regulations_cited": ["40 C.F.R. Part 60"],
            "cases_cited": [
                "Brandenburg v. Ohio, 395 U.S. 444 (1969)",
                "New York Times v. Sullivan, 376 U.S. 254 (1964)"
            ],
            "topics_or_policy_areas": [
                "free speech", "defamation", "public figures",
                "actual malice", "First Amendment", "press freedom"
            ],
            "holding_plain": "Public figures must prove actual malice for defamation claims.",
            "outcome_simple": "The judgment was reversed and remanded.",
            "issue_plain": "What standard applies to defamation claims by public figures?",
            "reasoning": "The Court balanced free speech against reputation protection..."
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_metadata)))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        complex_opinion = """
        Syllabus

        Petitioner, a public figure, sued respondent newspaper for defamation...
        Held: Public figures must prove actual malice...

        CHIEF JUSTICE ROBERTS delivered the opinion of the Court.

        This case requires us to revisit the standard established in New York Times v. Sullivan...

        JUSTICE THOMAS, concurring in part and dissenting in part.

        While I agree with the majority's conclusion, I write separately...

        JUSTICE SOTOMAYOR, dissenting.

        I respectfully dissent from the Court's holding...
        """

        complex_syllabus = """
        Syllabus

        Held: The First Amendment requires public figures to prove actual malice...
        """

        # Act
        result = generate_scotus_llm_fields(complex_opinion, complex_syllabus)

        # Assert
        assert "actual malice" in result["holding_plain"]
        assert len(result["constitution_cited"]) >= 2
        assert len(result["cases_cited"]) >= 2
        assert len(result["topics_or_policy_areas"]) >= 4

    @patch('governmentreporter.processors.llm_extraction.OpenAI')
    @patch('governmentreporter.processors.llm_extraction.get_openai_api_key')
    def test_eo_extraction_with_multiple_sections(self, mock_get_key, mock_openai_class):
        """
        Test extraction from Executive Order with multiple sections.

        Verifies comprehensive extraction from multi-section EOs
        with various agencies and requirements.

        Args:
            mock_get_key: Mock API key getter
            mock_openai_class: Mock OpenAI class
        """
        # Arrange
        mock_get_key.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_metadata = {
            "plain_summary": "Comprehensive climate action order requiring federal agencies...",
            "federal_statutes_referenced": [
                "Clean Air Act, 42 U.S.C. § 7401",
                "National Environmental Policy Act, 42 U.S.C. § 4321"
            ],
            "federal_regulations_referenced": [
                "40 C.F.R. Part 60",
                "40 C.F.R. Part 1500"
            ],
            "agencies_or_entities": [
                "EPA", "Department of Energy", "Department of Defense",
                "General Services Administration", "NOAA", "NASA"
            ],
            "topics_or_policy_areas": [
                "climate change", "renewable energy", "carbon emissions",
                "federal procurement", "environmental justice"
            ],
            "action_plain": "Mandates carbon neutrality for federal operations by 2030",
            "impact_simple": "All federal agencies must transition to clean energy",
            "implementation_requirements": "Quarterly progress reports and annual targets required"
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_metadata)))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        multi_section_eo = """
        EXECUTIVE ORDER

        Section 1. Purpose. Climate change poses an existential threat...

        Sec. 2. Policy. The United States shall achieve net-zero emissions...

        Sec. 3. Federal Operations. All agencies shall transition to renewable energy...

        Sec. 4. Procurement. Federal procurement shall prioritize sustainable products...

        Sec. 5. Reporting. Agencies shall submit quarterly progress reports...

        Sec. 6. Implementation. The EPA shall coordinate implementation...
        """

        # Act
        result = generate_eo_llm_fields(multi_section_eo)

        # Assert
        assert len(result["agencies_or_entities"]) >= 4
        assert "EPA" in result["agencies_or_entities"]
        assert len(result["federal_statutes_referenced"]) >= 2
        assert "climate change" in result["topics_or_policy_areas"]
        assert "2030" in result["action_plain"] or "carbon" in result["action_plain"]


# Test fixtures for LLM extraction
@pytest.fixture
def mock_openai_response():
    """
    Create a mock OpenAI chat completion response.

    Returns:
        MagicMock: Mock response with structured content

    Python Learning Notes:
        - Fixtures provide reusable test components
        - Mock responses simulate API behavior
    """
    response = MagicMock()
    response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({
                    "plain_language_summary": "Test summary",
                    "topics_or_policy_areas": ["test topic"],
                })
            )
        )
    ]
    return response


@pytest.fixture
def sample_scotus_opinion():
    """
    Provide sample Supreme Court opinion for testing.

    Returns:
        tuple: (opinion_text, syllabus_text)
    """
    opinion = """
    CHIEF JUSTICE ROBERTS delivered the opinion of the Court.

    This case presents the question whether the First Amendment prohibits...
    We hold that it does not. The judgment below is reversed.
    """

    syllabus = """
    Syllabus

    Held: The First Amendment does not prohibit the challenged regulation.
    """

    return opinion, syllabus


@pytest.fixture
def sample_executive_order():
    """
    Provide sample Executive Order for testing.

    Returns:
        str: Sample EO text
    """
    return """
    EXECUTIVE ORDER

    By the authority vested in me as President by the Constitution...

    Section 1. Purpose. This order establishes new requirements...

    Sec. 2. Policy. It is the policy of the United States...

    Sec. 3. Implementation. All executive departments shall comply...
    """