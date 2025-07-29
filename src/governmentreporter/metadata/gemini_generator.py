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
        prompt = self._create_scotus_metadata_prompt(plain_text)

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
            return self._validate_scotus_metadata(metadata)

        except (json.JSONDecodeError, Exception) as e:
            # If parsing fails, return minimal metadata
            return {
                "summary": "Unable to extract summary",
                "topics": [],
                "author": None,
                "majority": [],
                "minority": [],
                "extraction_error": str(e),
            }

    def _create_scotus_metadata_prompt(self, plain_text: str) -> str:
        """Create a prompt for extracting Supreme Court opinion metadata."""
        return f"""
You are a legal expert analyzing a US Supreme Court opinion. Extract the following metadata from the provided text and return it as a JSON object with exactly these fields:

1. "summary": A paragraph summarizing the case that includes the legal issue, holding, and rationale. Use the case syllabus if available.
2. "topics": An array of 5-10 topic tags including the legal areas in dispute (examples: "1st Amendment", "free speech", "voting rights act", "constitutional law", "civil rights", "commerce clause", etc.)
3. "author": Full name (first and last) of the majority opinion author, or null if not identifiable
4. "majority": Array of last names of justices in the majority, or empty array if not identifiable
5. "minority": Array of last names of justices in the minority/dissent, or empty array if not identifiable

Requirements:
- Return ONLY a valid JSON object with these exact field names
- Ensure all field names are in lowercase
- The summary should be 2-4 sentences focusing on the legal issue, court's holding, and key reasoning
- Topics should be specific legal concepts, not generic terms
- Justice names should be last names only for majority/minority arrays
- If information cannot be determined, use null for strings or empty arrays for lists

Supreme Court Opinion Text:
{plain_text[:15000]}  # Limit text to avoid token limits

Return the JSON object:
"""

    def _validate_scotus_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the extracted metadata."""
        validated = {
            "summary": metadata.get("summary", ""),
            "topics": metadata.get("topics", []),
            "author": metadata.get("author"),
            "majority": metadata.get("majority", []),
            "minority": metadata.get("minority", []),
        }

        # Ensure topics is a list
        if not isinstance(validated["topics"], list):
            validated["topics"] = []

        # Ensure majority/minority are lists
        if not isinstance(validated["majority"], list):
            validated["majority"] = []
        if not isinstance(validated["minority"], list):
            validated["minority"] = []

        # Clean up topic strings
        validated["topics"] = [
            topic.strip()
            for topic in validated["topics"]
            if isinstance(topic, str) and topic.strip()
        ]

        # Clean up justice name lists
        validated["majority"] = [
            name.strip()
            for name in validated["majority"]
            if isinstance(name, str) and name.strip()
        ]
        validated["minority"] = [
            name.strip()
            for name in validated["minority"]
            if isinstance(name, str) and name.strip()
        ]

        return validated

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

5. "holding": A single sentence stating the court's holding/decision from the syllabus or conclusion

Requirements:
- Return ONLY a valid JSON object with these exact field names
- All field names must be in lowercase  
- For constitutional_provisions and statutes_interpreted, be very precise with citations
- Only include actual legal citations, not general references
- If information cannot be determined, use empty arrays for lists or null for strings
- The holding should be a concise statement of what the court decided

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

        # Clean up holding
        if validated["holding"] and isinstance(validated["holding"], str):
            validated["holding"] = validated["holding"].strip()
        else:
            validated["holding"] = None

        return validated
