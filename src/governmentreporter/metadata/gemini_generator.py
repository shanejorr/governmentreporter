"""Gemini AI-powered metadata generation for legal documents."""

import json
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from ..utils.config import get_google_gemini_api_key


class GeminiMetadataGenerator:
    """Generate metadata for legal documents using Google's Gemini 2.5 Flash-Lite."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini metadata generator.

        Args:
            api_key: Google Gemini API key. If None, will fetch from environment.
        """
        self.api_key = api_key or get_google_gemini_api_key()
        genai.configure(api_key=self.api_key)

        # Use Gemini 2.5 Flash-Lite as specified
        self.model = genai.GenerativeModel("gemini-2.5-flash-lite")

    def generate_scotus_metadata(self, plain_text: str) -> Dict[str, Any]:
        """Generate metadata for a Supreme Court opinion.

        Args:
            plain_text: The full text of the Supreme Court opinion

        Returns:
            Dict containing extracted metadata
        """
        prompt = self._create_legal_metadata_prompt(plain_text)

        try:
            response = self.model.generate_content(prompt)

            # Strip markdown code fences if present
            response_text = response.text.strip()
            if response_text.startswith("```json") and response_text.endswith("```"):
                response_text = response_text[7:-3].strip()  # Remove ```json and ```
            elif response_text.startswith("```") and response_text.endswith("```"):
                response_text = response_text[3:-3].strip()  # Remove ``` and ```

            metadata = json.loads(response_text)

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

    def extract_legal_metadata(self, plain_text: str) -> Dict[str, Any]:
        """Extract comprehensive legal metadata for Supreme Court opinion chunking.

        Args:
            plain_text: The full text of the Supreme Court opinion

        Returns:
            Dict containing extracted legal metadata
        """
        prompt = self._create_legal_metadata_prompt(plain_text)

        try:
            response = self.model.generate_content(prompt)

            # Strip markdown code fences if present
            response_text = response.text.strip()
            if response_text.startswith("```json") and response_text.endswith("```"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```") and response_text.endswith("```"):
                response_text = response_text[3:-3].strip()

            metadata = json.loads(response_text)

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
        """Create a prompt for extracting legal metadata from Supreme Court opinions."""
        return f"""
You are a legal expert analyzing a US Supreme Court opinion. Extract the following metadata from the provided text and return it as a JSON object with exactly these fields:

1. "legal_topics": Array of primary areas of law addressed in this case (e.g., "Constitutional Law", "Administrative Law", "First Amendment", "Commerce Clause", "Due Process", "Civil Rights")

2. "key_legal_questions": Array of 2-4 specific legal questions that the court addressed in this case

3. "constitutional_provisions": Array of constitutional provisions cited in the opinion. Only include specific amendment/clause references (e.g., "First Amendment", "Art. I, § 9, cl. 7", "Fourteenth Amendment"). Do NOT include general references to "the Constitution"

4. "statutes_interpreted": Array of specific statutes cited or interpreted by the court. Use precise bluebook citation format (e.g., "42 U.S.C. § 1983", "15 U.S.C. § 1692"). Do NOT include general statutory references

5. "holding": A single sentence stating the court's holding/decision from the syllabus or conclusion. (taken from syllabus)

6. "procedural_outcome": The court's procedural decision regarding the lower court's ruling (e.g., "Reversed", "Affirmed", "Reversed and remanded", "Affirmed in part and reversed in part", "Vacated and remanded"). Extract from the court's final disposition.

7. "vote_breakdown": The voting breakdown of the justices (e.g., "9-0", "7-2", "6-3", "5-4", "Unanimous", "Per curiam"). Extract from the opinion header or conclusion.

Requirements:
- Return ONLY a valid JSON object with these exact field names
- All field names must be in lowercase  
- For constitutional_provisions and statutes_interpreted, be very precise with citations
- Use legal bluebook format when citing statutes and constitutional provisions
- Only include actual legal citations, not general references
- If information cannot be determined, use empty arrays for lists or null for strings
- The holding should be a concise statement of what the court decided
- For procedural_outcome, use standard legal terminology for dispositions
- For vote_breakdown, prefer numerical format (e.g., "9-0") over descriptive terms when both are available

Supreme Court Opinion Text:
{plain_text[:20000]}  # Limit text to avoid token limits

Return the JSON object:
"""

    def _validate_legal_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the extracted legal metadata."""
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
