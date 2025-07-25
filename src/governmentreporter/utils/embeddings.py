"""Google embeddings generation for text content."""

import google.generativeai as genai
from typing import List
from .config import get_google_gemini_api_key


class GoogleEmbeddingsClient:
    """Client for generating embeddings using Google's embedding models."""
    
    def __init__(self, api_key: str = None):
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
                title="Legal Document"
            )
            
            return result['embedding']
            
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate an embedding for a search query.
        
        Args:
            query: The search query text
            
        Returns:
            List of floats representing the query embedding vector
        """
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=query,
                task_type="retrieval_query"
            )
            
            return result['embedding']
            
        except Exception as e:
            raise Exception(f"Failed to generate query embedding: {str(e)}")
    
    def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings