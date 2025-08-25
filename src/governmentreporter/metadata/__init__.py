"""Metadata generation using AI models.

This module provides tools for extracting structured metadata from legal documents
using artificial intelligence models. Currently focused on OpenAI's GPT-5 API
for analyzing Supreme Court opinions and other legal texts.

The metadata module is part of the GovernmentReporter system's data processing
pipeline, where documents are analyzed to extract semantic meaning and structured
information that can be stored alongside vector embeddings in Qdrant.

Python Learning Notes:
- This is a package initialization file (__init__.py) that controls what gets
  imported when someone does "from governmentreporter.metadata import ..."
- The __all__ list explicitly defines what symbols should be available for import
- This pattern keeps the public API clean and prevents internal modules from
  being accidentally imported

Components:
- GPT5MetadataGenerator: Main class for AI-powered metadata extraction using
  OpenAI's GPT-5-nano model

Integration Points:
- Connects to OpenAI API for natural language processing
- Works with the database module to store extracted metadata
- Integrates with the APIs module to process documents from government sources
- Used by the main indexing pipeline to enrich document storage

Example Usage:
    from governmentreporter.metadata import GPT5MetadataGenerator

    generator = GPT5MetadataGenerator()
    metadata = generator.extract_legal_metadata(document_text)
"""

from .gpt5_generator import GPT5MetadataGenerator

__all__ = ["GPT5MetadataGenerator"]
