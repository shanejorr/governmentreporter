"""GPT-5 AI-powered metadata generation for legal documents.

This module implements intelligent metadata extraction from legal documents,
specifically designed for US Supreme Court opinions. It uses OpenAI's GPT-5-nano
model to analyze legal text and extract structured information like
legal topics, constitutional provisions, statutes, and case outcomes.

The extracted metadata serves multiple purposes in the GovernmentReporter system:
1. Enhances search capabilities by providing structured legal concepts
2. Enables better document categorization and filtering
3. Supports semantic search alongside vector embeddings
4. Provides context for LLM interactions with legal documents

Python Learning Notes:
- This module demonstrates advanced API integration with OpenAI's AI services
- Shows error handling patterns for external API calls
- Illustrates JSON parsing and data validation techniques
- Uses type hints extensively for better code documentation
- Implements the strategy pattern with different prompt templates

Key Design Patterns:
- Factory pattern: Model creation is handled by the OpenAI library
- Template method pattern: Prompt creation is separated from execution
- Error handling: Graceful degradation when AI extraction fails

Integration with GovernmentReporter:
- Called during document indexing to enrich metadata
- Works with Qdrant storage to persist extracted information
- Integrates with the utils.config module for API key management
- Designed to process documents from the APIs module (CourtListener, etc.)
"""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from openai import OpenAI

from ..utils import get_logger
from ..utils.config import get_openai_api_key


class LegalMetadata(BaseModel):
    """Pydantic model for structured legal metadata output.
    
    This model defines the schema for legal metadata extraction using
    OpenAI's structured output feature. Each field is carefully designed
    to capture specific legal information from Supreme Court opinions.
    
    Python Learning Notes:
    - Pydantic BaseModel provides automatic validation and serialization
    - Optional[str] means the field can be a string or None
    - List[str] indicates a list of strings (array in JSON)
    - The model automatically converts to/from JSON format
    """
    legal_topics: List[str]
    key_legal_questions: List[str]
    constitutional_provisions: List[str]
    statutes_interpreted: List[str]
    holding: Optional[str]
    procedural_outcome: Optional[str]
    vote_breakdown: Optional[str]


class GPT5MetadataGenerator:
    """Generate metadata for legal documents using OpenAI's GPT-5-nano.

    This class provides AI-powered analysis of legal documents to extract structured
    metadata that enhances search and categorization capabilities. It specifically
    targets Supreme Court opinions but could be extended to other legal document types.

    The class handles the complete workflow from API initialization to metadata
    validation, with robust error handling for production use.

    Python Learning Notes:
    - This is a service class that encapsulates AI functionality
    - Uses dependency injection for the API key (can be provided or auto-detected)
    - Implements the single responsibility principle (only handles metadata extraction)
    - Shows how to integrate with external AI APIs safely

    Attributes:
        api_key (str): OpenAI API key for authentication
        client (OpenAI): Configured OpenAI client instance
        model (str): Model identifier (gpt-5-nano)

    Example Usage:
        # Basic usage with auto-detected API key
        generator = GPT5MetadataGenerator()
        metadata = generator.extract_legal_metadata(opinion_text)

        # Usage with explicit API key
        generator = GPT5MetadataGenerator(api_key="your-key-here")
        metadata = generator.extract_legal_metadata(opinion_text)

    Integration Points:
        - Uses utils.config.get_openai_api_key() for API key management
        - Returns metadata compatible with Qdrant storage format
        - Designed to work with document text from the APIs module
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the GPT-5 metadata generator.

        Sets up the connection to OpenAI's API and configures the model
        for legal document analysis. The initialization includes API key
        management and model selection.

        Python Learning Notes:
        - Uses Optional[str] type hint to indicate api_key can be None
        - Demonstrates the "or" operator for default value assignment
        - Shows how to configure external APIs in Python classes
        - The OpenAI() call creates a client for API interaction

        Args:
            api_key (Optional[str]): OpenAI API key for authentication.
                If None, the key will be automatically retrieved from the
                environment using the config utility. This allows for flexible
                deployment where keys can be injected or detected.

        Raises:
            ValueError: If no API key is found in either parameter or environment
            AuthenticationError: If the provided API key is invalid

        Note:
            The GPT-5-nano model is specifically chosen for its balance of
            performance and cost-effectiveness for metadata extraction tasks.
            It provides sufficient capability for legal text analysis while
            being more economical than larger models.
        """
        self.api_key = api_key or get_openai_api_key()
        self.logger = get_logger(__name__)

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        
        # Use GPT-5-nano as specified
        self.model = "gpt-5-nano"
        self.logger.info(
            "GPT5MetadataGenerator initialized with gpt-5-nano model"
        )

    def extract_legal_metadata(self, plain_text: str) -> Dict[str, Any]:
        """Extract comprehensive legal metadata for Supreme Court opinion chunking.

        This method performs intelligent analysis of legal text to extract structured
        metadata that enhances document searchability and categorization. It uses
        the GPT-5 Responses API with structured outputs for consistent results.

        The extraction process follows these steps:
        1. Create a specialized prompt for legal analysis
        2. Send the text to GPT-5-nano for processing with minimal reasoning
        3. Parse and validate the structured response
        4. Return structured metadata or fallback values on error

        Python Learning Notes:
        - Demonstrates use of OpenAI's new Responses API
        - Shows structured output with Pydantic models
        - Uses exception handling with try/except blocks
        - Implements graceful degradation (returns partial data on failure)
        - Type hints show the method contract clearly

        Args:
            plain_text (str): The complete text of the Supreme Court opinion
                to analyze. Should include the full opinion text for best
                results, though the method will truncate very long texts
                to stay within API limits.

        Returns:
            Dict[str, Any]: A dictionary containing structured legal metadata
                with the following guaranteed keys:
                - 'legal_topics' (List[str]): Primary areas of law addressed
                - 'key_legal_questions' (List[str]): Main legal questions
                - 'constitutional_provisions' (List[str]): Referenced amendments/clauses
                - 'statutes_interpreted' (List[str]): Specific statutes cited
                - 'holding' (Optional[str]): Court's main decision/holding
                - 'procedural_outcome' (Optional[str]): How the case was resolved
                - 'vote_breakdown' (Optional[str]): Justice voting pattern
                - 'extraction_error' (Optional[str]): Error message if parsing failed

        Raises:
            ValueError: If plain_text is empty or None
            APIError: If the OpenAI API returns an error (rare, handled internally)

        Example:
            generator = GPT5MetadataGenerator()
            text = "In the matter of Brown v. Board of Education..."
            metadata = generator.extract_legal_metadata(text)

            # metadata will contain:
            # {
            #     'legal_topics': ['Constitutional Law', 'Civil Rights'],
            #     'key_legal_questions': ['Does segregation violate equal protection?'],
            #     'constitutional_provisions': ['Fourteenth Amendment'],
            #     'statutes_interpreted': [],
            #     'holding': 'Segregation in public schools is unconstitutional',
            #     'procedural_outcome': 'Reversed',
            #     'vote_breakdown': '9-0'
            # }

        Integration Notes:
            The returned metadata is designed to integrate seamlessly with:
            - Qdrant storage for vector database persistence
            - Search interfaces for filtered document retrieval
            - LLM context enhancement for better legal reasoning
        """
        prompt = self._create_legal_metadata_prompt(plain_text)

        try:
            # Use GPT-5's new Responses API with structured output
            response = self.client.responses.parse(
                model=self.model,
                input=prompt,
                text_format=LegalMetadata,
                reasoning={"effort": "minimal"},  # Minimal reasoning for speed
                text={"verbosity": "low"}  # Low verbosity for concise output
            )

            # Extract the parsed metadata
            if response.output_parsed:
                metadata = response.output_parsed.model_dump()
            else:
                # If parsing failed, try to get raw output
                metadata = json.loads(response.output_text)

            # Validate and clean the response
            return self._validate_legal_metadata(metadata)

        except (json.JSONDecodeError, Exception) as e:
            # If parsing fails, return minimal metadata
            return {
                "legal_topics": [],
                "key_legal_questions": [],
                "constitutional_provisions": [],
                "statutes_interpreted": [],
                "holding": None,
                "procedural_outcome": None,
                "vote_breakdown": None,
                "extraction_error": str(e),
            }

    def _create_legal_metadata_prompt(self, plain_text: str) -> str:
        """Create a specialized prompt for extracting legal metadata from Supreme Court opinions.

        This method constructs a detailed prompt that guides the AI model to extract
        specific legal information in a structured format. The prompt is designed
        for the GPT-5 Responses API input format.

        Key prompt engineering strategies used:
        1. Role specification: Establishes the AI as a "legal expert"
        2. Structured output: Requires specific JSON format with exact field names
        3. Example guidance: Provides format examples for complex citations
        4. Constraint specification: Defines what to include/exclude
        5. Error handling: Specifies fallback values for missing information

        Python Learning Notes:
        - Returns a simple string prompt for the Responses API
        - Uses f-string formatting to inject variables
        - Demonstrates string slicing with plain_text[:20000] to limit length
        - Clear instructions ensure consistent AI responses

        Args:
            plain_text (str): The Supreme Court opinion text to analyze.
                The method automatically truncates to 20,000 characters
                to stay within API token limits while preserving the most
                important content (usually at the beginning of opinions).

        Returns:
            str: A comprehensive prompt string formatted for optimal AI
                extraction of legal metadata. The prompt includes clear
                instructions for legal analysis and specific requirements.

        Design Notes:
            The 20,000 character limit is chosen to:
            - Stay well within GPT-5 token limits
            - Capture the most important parts of legal opinions (intro, holding)
            - Balance thoroughness with API cost considerations
            - Ensure consistent processing times
        """
        return f"""You are a legal expert analyzing a US Supreme Court opinion. Extract the following metadata from the provided text and return it as a structured JSON object with exactly these fields:

1. "legal_topics": Array of primary areas of law addressed in this case (e.g., "Constitutional Law", "Administrative Law", "First Amendment", "Commerce Clause", "Due Process", "Civil Rights")
2. "key_legal_questions": Array of 2-4 specific legal questions that the court addressed in this case
3. "constitutional_provisions": Array of constitutional provisions cited in the opinion. Only include specific amendment/clause references (e.g., "First Amendment", "Art. I, § 9, cl. 7", "Fourteenth Amendment"). Do NOT include general references to "the Constitution"
4. "statutes_interpreted": Array of specific statutes cited or interpreted by the court. Use precise bluebook citation format (e.g., "42 U.S.C. § 1983", "15 U.S.C. § 1692"). Do NOT include general statutory references
5. "holding": A single sentence stating the court's holding/decision from the syllabus or conclusion. (taken from syllabus)
6. "procedural_outcome": The court's procedural decision regarding the lower court's ruling (e.g., "Reversed", "Affirmed", "Reversed and remanded", "Affirmed in part and reversed in part", "Vacated and remanded"). Extract from the court's final disposition.
7. "vote_breakdown": The voting breakdown of the justices (e.g., "9-0", "7-2", "6-3", "5-4", "Unanimous", "Per curiam"). Extract from the opinion header or conclusion.

Requirements:
- Be very precise with citations using legal bluebook format
- Only include actual legal citations, not general references
- If information cannot be determined, use empty arrays for lists or null for strings
- The holding should be a concise statement of what the court decided
- For procedural_outcome, use standard legal terminology for dispositions
- For vote_breakdown, prefer numerical format (e.g., "9-0") over descriptive terms when both are available

Supreme Court Opinion Text:
{plain_text[:20000]}"""

    def _validate_legal_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the extracted legal metadata from AI response.

        This method ensures that the AI-generated metadata conforms to expected
        formats and contains clean, usable data. It performs comprehensive validation
        and sanitization to prevent downstream processing errors.

        The validation process includes:
        1. Ensuring all required fields are present with correct types
        2. Converting non-list fields to empty lists where appropriate
        3. Cleaning string data (trimming whitespace, removing empty strings)
        4. Standardizing null/None values for consistency

        Python Learning Notes:
        - Demonstrates the dict.get() method with default values
        - Uses isinstance() for runtime type checking
        - Shows list comprehension with conditional filtering
        - Illustrates defensive programming practices
        - Uses loops to apply similar operations to multiple fields

        Args:
            metadata (Dict[str, Any]): Raw metadata dictionary returned from
                the AI model. May contain inconsistent types, extra fields,
                or missing required fields due to AI response variability.

        Returns:
            Dict[str, Any]: Cleaned and validated metadata dictionary with:
                - All required fields present and correctly typed
                - List fields guaranteed to contain only non-empty strings
                - String fields properly trimmed or set to None
                - Consistent structure for downstream processing

        Validation Rules:
            Array Fields (legal_topics, key_legal_questions, etc.):
            - Must be lists; converted to empty list if not
            - Items must be non-empty strings after trimming
            - Empty or whitespace-only strings are removed

            String Fields (holding, procedural_outcome, vote_breakdown):
            - Must be strings or None
            - Whitespace is trimmed from valid strings
            - Empty strings after trimming become None

        Example:
            # Input from AI (potentially messy)
            raw_metadata = {
                'legal_topics': ['  Contract Law  ', '', 'Torts'],
                'holding': '   The court decided...   ',
                'extra_field': 'ignored'
            }

            # Output after validation
            clean_metadata = {
                'legal_topics': ['Contract Law', 'Torts'],  # cleaned strings
                'key_legal_questions': [],  # missing field becomes empty list
                'constitutional_provisions': [],
                'statutes_interpreted': [],
                'holding': 'The court decided...',  # trimmed string
                'procedural_outcome': None,  # missing field becomes None
                'vote_breakdown': None
            }

        Error Handling:
            This method is designed to never raise exceptions. Even severely
            malformed input will result in a valid metadata structure with
            appropriate default values. This ensures the metadata extraction
            process continues to function even when AI responses are unexpected.
        """
        validated = {
            "legal_topics": metadata.get("legal_topics", []),
            "key_legal_questions": metadata.get("key_legal_questions", []),
            "constitutional_provisions": metadata.get("constitutional_provisions", []),
            "statutes_interpreted": metadata.get("statutes_interpreted", []),
            "holding": metadata.get("holding"),
            "procedural_outcome": metadata.get("procedural_outcome"),
            "vote_breakdown": metadata.get("vote_breakdown"),
        }

        # Ensure all array fields are lists
        for field in [
            "legal_topics",
            "key_legal_questions",
            "constitutional_provisions",
            "statutes_interpreted",
        ]:
            if not isinstance(validated[field], list):
                validated[field] = []
            else:
                # Clean up strings in arrays
                validated[field] = [
                    item.strip()
                    for item in validated[field]
                    if isinstance(item, str) and item.strip()
                ]

        # Clean up string fields
        for field in ["holding", "procedural_outcome", "vote_breakdown"]:
            if validated[field] and isinstance(validated[field], str):
                validated[field] = validated[field].strip()
            else:
                validated[field] = None

        return validated