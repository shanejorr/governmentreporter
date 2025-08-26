"""
Example output for chunking.py methods with return values.

This file demonstrates the methods in chunking.py that return output
and can be run in the main guard pattern.
"""

import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.governmentreporter.processors.chunking import (
    get_chunking_config,
    count_tokens,
    normalize_whitespace,
    chunk_text_with_tokens,
    chunk_supreme_court_opinion,
    chunk_executive_order,
    overlap_tokens,
    ChunkingConfig
)


def main():
    """Run examples of chunking.py methods that return output."""
    results = {}
    
    # Test get_chunking_config
    try:
        scotus_config = get_chunking_config("scotus")
        eo_config = get_chunking_config("eo")
        
        results["get_chunking_config"] = {
            "method": "get_chunking_config()",
            "result": {
                "scotus": {
                    "min_tokens": scotus_config.min_tokens,
                    "target_tokens": scotus_config.target_tokens,
                    "max_tokens": scotus_config.max_tokens,
                    "overlap_ratio": scotus_config.overlap_ratio
                },
                "eo": {
                    "min_tokens": eo_config.min_tokens,
                    "target_tokens": eo_config.target_tokens,
                    "max_tokens": eo_config.max_tokens,
                    "overlap_ratio": eo_config.overlap_ratio
                }
            }
        }
    except Exception as e:
        results["get_chunking_config"] = {
            "method": "get_chunking_config()",
            "error": str(e)
        }
    
    # Test count_tokens
    try:
        test_texts = [
            "Short text.",
            "This is a medium length text that should have more tokens than the short one.",
            "This is a much longer text that contains multiple sentences and should demonstrate how the token counting works. It includes various punctuation marks, numbers like 123 and 456, and different types of words including technical terms.",
            ""  # Empty text
        ]
        
        token_results = {}
        for i, text in enumerate(test_texts):
            token_count = count_tokens(text)
            token_results[f"text_{i}"] = {
                "text": text if len(text) < 50 else text[:50] + "...",
                "character_count": len(text),
                "token_count": token_count,
                "chars_per_token": len(text) / token_count if token_count > 0 else 0
            }
        
        results["count_tokens"] = {
            "method": "count_tokens()",
            "result": token_results
        }
    except Exception as e:
        results["count_tokens"] = {
            "method": "count_tokens()",
            "error": str(e)
        }
    
    # Test normalize_whitespace
    try:
        test_strings = [
            "Normal text with  extra   spaces.",
            "Text with\n\n\nmultiple\n\n\nblank\n\nlines.",
            "   Leading and trailing spaces   ",
            "Mixed\n  \n\n  whitespace\n\n\n\nissues.",
            ""
        ]
        
        whitespace_results = {}
        for i, text in enumerate(test_strings):
            normalized = normalize_whitespace(text)
            whitespace_results[f"test_{i}"] = {
                "original": repr(text),
                "normalized": repr(normalized)
            }
        
        results["normalize_whitespace"] = {
            "method": "normalize_whitespace()",
            "result": whitespace_results
        }
    except Exception as e:
        results["normalize_whitespace"] = {
            "method": "normalize_whitespace()",
            "error": str(e)
        }
    
    # Test overlap_tokens
    try:
        scotus_config = get_chunking_config("scotus")
        eo_config = get_chunking_config("eo")
        
        overlap_results = {
            "scotus": {
                "config": {
                    "target_tokens": scotus_config.target_tokens,
                    "overlap_ratio": scotus_config.overlap_ratio
                },
                "overlap_tokens": overlap_tokens(scotus_config)
            },
            "eo": {
                "config": {
                    "target_tokens": eo_config.target_tokens,
                    "overlap_ratio": eo_config.overlap_ratio
                },
                "overlap_tokens": overlap_tokens(eo_config)
            }
        }
        
        results["overlap_tokens"] = {
            "method": "overlap_tokens()",
            "result": overlap_results
        }
    except Exception as e:
        results["overlap_tokens"] = {
            "method": "overlap_tokens()",
            "error": str(e)
        }
    
    # Test chunk_text_with_tokens
    try:
        sample_text = """This is a sample text for testing the chunking functionality. It contains multiple sentences and paragraphs to demonstrate how the text chunking algorithm works with token-based splitting.

The algorithm should respect sentence boundaries when possible and maintain reasonable chunk sizes. This helps ensure that the chunks are meaningful and can be processed effectively by downstream systems.

Here is another paragraph to provide more content for chunking. The system should be able to handle various text structures and maintain coherent chunks that preserve the meaning of the original text."""
        
        scotus_config = get_chunking_config("scotus")
        ov = overlap_tokens(scotus_config)
        
        chunks = chunk_text_with_tokens(
            text=sample_text,
            section_label="Test Section",
            min_tokens=scotus_config.min_tokens,
            target_tokens=scotus_config.target_tokens,
            max_tokens=scotus_config.max_tokens,
            overlap_tokens=ov
        )
        
        chunk_results = []
        for i, (chunk_text, metadata) in enumerate(chunks):
            chunk_results.append({
                "chunk_index": i,
                "text_preview": chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text,
                "text_length": len(chunk_text),
                "metadata": metadata
            })
        
        results["chunk_text_with_tokens"] = {
            "method": "chunk_text_with_tokens()",
            "result": {
                "total_chunks": len(chunk_results),
                "chunks": chunk_results
            }
        }
    except Exception as e:
        results["chunk_text_with_tokens"] = {
            "method": "chunk_text_with_tokens()",
            "error": str(e)
        }
    
    # Test chunk_supreme_court_opinion
    try:
        sample_scotus = """SYLLABUS
        
The Court held that the Fourth Amendment requires a warrant for searching digital devices seized incident to arrest.

JUSTICE ROBERTS delivered the opinion of the Court.

I.

The question presented is whether police may search digital information on cell phones without a warrant. We hold that they generally may not.

II.

Digital devices differ from physical objects due to their immense storage capacity and breadth of private information.

JUSTICE ALITO, concurring.

I agree with the Court's holding but write separately to emphasize the need for legislative action."""

        chunks, syllabus = chunk_supreme_court_opinion(sample_scotus)
        
        chunk_results = []
        for i, (chunk_text, metadata) in enumerate(chunks):
            chunk_results.append({
                "chunk_index": i,
                "text_preview": chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text,
                "section_label": metadata.get("section_label"),
                "token_count": metadata.get("chunk_token_count")
            })
        
        results["chunk_supreme_court_opinion"] = {
            "method": "chunk_supreme_court_opinion()",
            "result": {
                "total_chunks": len(chunk_results),
                "syllabus_extracted": syllabus[:100] + "..." if syllabus and len(syllabus) > 100 else syllabus,
                "chunks": chunk_results
            }
        }
    except Exception as e:
        results["chunk_supreme_court_opinion"] = {
            "method": "chunk_supreme_court_opinion()",
            "error": str(e)
        }
    
    # Test chunk_executive_order
    try:
        sample_eo = """Executive Order 14999

By the authority vested in me as President, I hereby order:

Section 1. Purpose. This order establishes new requirements for federal climate policy.

Sec. 2. Policy. (a) All agencies shall consider climate impacts.
(b) The EPA shall develop new standards.
    (i) Standards for emissions
    (ii) Standards for efficiency

Sec. 3. Implementation. Agencies shall report progress quarterly."""

        chunks = chunk_executive_order(sample_eo)
        
        chunk_results = []
        for i, (chunk_text, metadata) in enumerate(chunks):
            chunk_results.append({
                "chunk_index": i,
                "text_preview": chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text,
                "section_label": metadata.get("section_label"),
                "token_count": metadata.get("chunk_token_count")
            })
        
        results["chunk_executive_order"] = {
            "method": "chunk_executive_order()",
            "result": {
                "total_chunks": len(chunk_results),
                "chunks": chunk_results
            }
        }
    except Exception as e:
        results["chunk_executive_order"] = {
            "method": "chunk_executive_order()",
            "error": str(e)
        }
    
    # Print results in pretty JSON format
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()