"""Gemini AI-powered metadata generation for legal documents."""

import google.generativeai as genai
import json
from typing import Dict, Any, List
from ..utils.config import get_google_gemini_api_key


class GeminiMetadataGenerator:
    """Generate metadata for legal documents using Google's Gemini 2.5 Flash-Lite."""
    
    def __init__(self, api_key: str = None):
        """Initialize the Gemini metadata generator.
        
        Args:
            api_key: Google Gemini API key. If None, will fetch from environment.
        """
        self.api_key = api_key or get_google_gemini_api_key()
        genai.configure(api_key=self.api_key)
        
        # Use Gemini 2.5 Flash-Lite as specified
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
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
            if response_text.startswith('```json') and response_text.endswith('```'):
                response_text = response_text[7:-3].strip()  # Remove ```json and ```
            elif response_text.startswith('```') and response_text.endswith('```'):
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
                "extraction_error": str(e)
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
            "minority": metadata.get("minority", [])
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
            topic.strip() for topic in validated["topics"] 
            if isinstance(topic, str) and topic.strip()
        ]
        
        # Clean up justice name lists
        validated["majority"] = [
            name.strip() for name in validated["majority"]
            if isinstance(name, str) and name.strip()
        ]
        validated["minority"] = [
            name.strip() for name in validated["minority"]
            if isinstance(name, str) and name.strip()
        ]
        
        return validated