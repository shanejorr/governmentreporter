"""Metadata generation using AI models.

This module provides tools for extracting structured metadata from legal documents
using artificial intelligence models. Currently focused on Google's Gemini API
for analyzing Supreme Court opinions and other legal texts.

The metadata module is part of the GovernmentReporter system's data processing
pipeline, where documents are analyzed to extract semantic meaning and structured
information that can be stored alongside vector embeddings in ChromaDB.

Python Learning Notes:
- This is a package initialization file (__init__.py) that controls what gets
  imported when someone does "from governmentreporter.metadata import ..."
- The __all__ list explicitly defines what symbols should be available for import
- This pattern keeps the public API clean and prevents internal modules from
  being accidentally imported

Components:
- GeminiMetadataGenerator: Main class for AI-powered metadata extraction using
  Google's Gemini 2.5 Flash-Lite model

Integration Points:
- Connects to Google Gemini API for natural language processing
- Works with the database module to store extracted metadata
- Integrates with the APIs module to process documents from government sources
- Used by the main indexing pipeline to enrich document storage

Example Usage:
    from governmentreporter.metadata import GeminiMetadataGenerator

    generator = GeminiMetadataGenerator()
    metadata = generator.extract_legal_metadata(document_text)
"""

from .gemini_generator import GeminiMetadataGenerator

__all__ = ["GeminiMetadataGenerator"]
