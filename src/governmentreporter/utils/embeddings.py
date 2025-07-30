"""Google embeddings generation for text content."""

from typing import List, Optional

import google.generativeai as genai

from .config import get_google_gemini_api_key


class GoogleEmbeddingsClient:
    """Client for generating embeddings using Google's embedding models."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Google embeddings client.

        Args:
            api_key: Google Gemini API key. If None, will fetch from environment.
        """
        self.api_key = api_key or get_google_gemini_api_key()
        genai.configure(api_key=self.api_key)

        # Use Google's text embedding model
        self.model_name = "models/text-embedding-004"

    def generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding for the given text.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        try:
            # Truncate text if too long (Google has token limits)
            if len(text) > 10000:
                text = text[:10000]

            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document",
                title="Legal Document",
            )

            return result["embedding"]

        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}")
