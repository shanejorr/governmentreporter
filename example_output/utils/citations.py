"""
Example output for citations.py methods with return values.

This file demonstrates the methods in citations.py that return output
and can be run in the main guard pattern.
"""

import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.governmentreporter.utils.citations import (
    build_bluebook_citation,
    format_cfr_citation,
    format_usc_citation,
    format_constitution_citation,
    parse_cfr_citations,
    parse_usc_citations,
    parse_constitution_citations
)


def main():
    """Run examples of citations.py methods that return output."""
    results = {}
    
    # Test build_bluebook_citation
    try:
        # Sample cluster data as would come from Court Listener
        sample_cluster_data = {
            "citations": [
                {
                    "type": 1,
                    "volume": "347",
                    "reporter": "U.S.",
                    "page": "483"
                },
                {
                    "type": 2,
                    "volume": "98",
                    "reporter": "S.Ct.",
                    "page": "873"
                }
            ],
            "date_filed": "1954-05-17"
        }
        
        citation = build_bluebook_citation(sample_cluster_data)
        results["build_bluebook_citation"] = {
            "method": "build_bluebook_citation()",
            "result": citation
        }
    except Exception as e:
        results["build_bluebook_citation"] = {
            "method": "build_bluebook_citation()",
            "error": str(e)
        }
    
    # Test format_cfr_citation
    try:
        cfr_examples = [
            {"title": "14", "section": "91.817", "year": None},
            {"title": "14", "section": "91.817", "year": "2025"},
            {"title": "42", "section": "1983.1(a)(2)", "year": "2024"}
        ]
        
        cfr_results = []
        for example in cfr_examples:
            citation = format_cfr_citation(
                example["title"], 
                example["section"], 
                example["year"]
            )
            cfr_results.append({
                "input": example,
                "output": citation
            })
        
        results["format_cfr_citation"] = {
            "method": "format_cfr_citation()",
            "result": cfr_results
        }
    except Exception as e:
        results["format_cfr_citation"] = {
            "method": "format_cfr_citation()",
            "error": str(e)
        }
    
    # Test format_usc_citation
    try:
        usc_examples = [
            {"title": "42", "section": "1983", "year": None},
            {"title": "12", "section": "5497", "year": "2018"},
            {"title": "18", "section": "1001(a)(2)", "year": "2024"}
        ]
        
        usc_results = []
        for example in usc_examples:
            citation = format_usc_citation(
                example["title"], 
                example["section"], 
                example["year"]
            )
            usc_results.append({
                "input": example,
                "output": citation
            })
        
        results["format_usc_citation"] = {
            "method": "format_usc_citation()",
            "result": usc_results
        }
    except Exception as e:
        results["format_usc_citation"] = {
            "method": "format_usc_citation()",
            "error": str(e)
        }
    
    # Test format_constitution_citation
    try:
        const_examples = [
            {"article": "I", "amendment": None, "section": "9", "clause": "7"},
            {"article": None, "amendment": "XIV", "section": "2", "clause": None},
            {"article": "III", "amendment": None, "section": None, "clause": None},
            {"article": "I", "amendment": "XIV", "section": None, "clause": None},  # Should return None
            {"article": None, "amendment": None, "section": None, "clause": None}   # Should return None
        ]
        
        const_results = []
        for example in const_examples:
            citation = format_constitution_citation(
                article=example["article"],
                amendment=example["amendment"],
                section=example["section"],
                clause=example["clause"]
            )
            const_results.append({
                "input": example,
                "output": citation
            })
        
        results["format_constitution_citation"] = {
            "method": "format_constitution_citation()",
            "result": const_results
        }
    except Exception as e:
        results["format_constitution_citation"] = {
            "method": "format_constitution_citation()",
            "error": str(e)
        }
    
    # Test parse_cfr_citations
    try:
        cfr_text_examples = [
            "The FAA shall repeal 14 CFR 91.817 and modify 14 C.F.R. § 91.818(a).",
            "Pursuant to 42 CFR Part 36 and 14 C.F.R. § 121.1(a)(1), agencies must comply.",
            "No CFR citations in this text."
        ]
        
        cfr_parse_results = []
        for text in cfr_text_examples:
            citations = parse_cfr_citations(text)
            cfr_parse_results.append({
                "text": text,
                "citations_found": citations
            })
        
        results["parse_cfr_citations"] = {
            "method": "parse_cfr_citations()",
            "result": cfr_parse_results
        }
    except Exception as e:
        results["parse_cfr_citations"] = {
            "method": "parse_cfr_citations()",
            "error": str(e)
        }
    
    # Test parse_usc_citations
    try:
        usc_text_examples = [
            "Under 42 U.S.C. § 1983, and pursuant to 12 U.S.C. 5497(a)(1), violations occur.",
            "See 18 USC § 1001 and 26 U.S.C. § 7701 for definitions.",
            "No USC citations in this text."
        ]
        
        usc_parse_results = []
        for text in usc_text_examples:
            citations = parse_usc_citations(text)
            usc_parse_results.append({
                "text": text,
                "citations_found": citations
            })
        
        results["parse_usc_citations"] = {
            "method": "parse_usc_citations()",
            "result": usc_parse_results
        }
    except Exception as e:
        results["parse_usc_citations"] = {
            "method": "parse_usc_citations()",
            "error": str(e)
        }
    
    # Test parse_constitution_citations
    try:
        const_text_examples = [
            "Under Art. I, § 9, cl. 7 and the Fifth Amendment, rights are protected.",
            "The Fourteenth Amendment and Article III provide protections.",
            "No constitutional citations in this text.",
            "The First Amendment and U.S. Const. art. II, § 1 are relevant."
        ]
        
        const_parse_results = []
        for text in const_text_examples:
            citations = parse_constitution_citations(text)
            const_parse_results.append({
                "text": text,
                "citations_found": citations
            })
        
        results["parse_constitution_citations"] = {
            "method": "parse_constitution_citations()",
            "result": const_parse_results
        }
    except Exception as e:
        results["parse_constitution_citations"] = {
            "method": "parse_constitution_citations()",
            "error": str(e)
        }
    
    # Print results in pretty JSON format
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()