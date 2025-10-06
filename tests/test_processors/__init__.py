"""
Unit tests for the processors module.

This test package provides comprehensive testing for all document processing
functionality including chunking, embedding generation, metadata extraction,
and payload building for Qdrant storage.

Test modules:
    - test_chunking: Tests for document chunking algorithms
    - test_embeddings: Tests for embedding generation with mocked OpenAI
    - test_llm_extraction: Tests for GPT-5-nano metadata generation
    - test_schema: Tests for Pydantic model validation
    - test_build_payloads: Tests for payload orchestration

Python Learning Notes:
    - This __init__.py file makes the directory a Python package
    - Test discovery will find all test_*.py files automatically
    - Each test module focuses on a specific component
"""
