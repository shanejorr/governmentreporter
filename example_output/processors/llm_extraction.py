"""
Example output for llm_extraction.py methods with return values.

This file demonstrates the methods in llm_extraction.py that return output
and can be run in the main guard pattern.
"""

import json
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.governmentreporter.processors.llm_extraction import (
    generate_eo_llm_fields, generate_scotus_llm_fields)


def main():
    """Run examples of llm_extraction.py methods that return output."""
    results = {}

    # Check if OpenAI API key is available
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        results["api_key_missing"] = {
            "method": "All LLM extraction methods",
            "error": "OPENAI_API_KEY not set in environment variables",
        }
        print(json.dumps(results, indent=2))
        return

    # Test generate_scotus_llm_fields
    try:
        sample_scotus_text = """SYLLABUS
        
Held: The Fourth Amendment requires police to obtain a warrant before conducting a search of digital devices seized incident to arrest.

The Court reasoned that digital devices differ from physical objects due to their immense storage capacity and the breadth of private information they contain.

JUSTICE ROBERTS delivered the opinion of the Court.

The question presented is whether the police may, without a warrant, search digital information on a cell phone seized from an individual who has been arrested. We hold that they generally may not.

The Fourth Amendment protects against unreasonable searches and seizures. Digital devices contain vast amounts of personal information that deserve constitutional protection."""

        sample_syllabus = """Held: The Fourth Amendment requires police to obtain a warrant before conducting a search of digital devices seized incident to arrest."""

        # Test with syllabus
        scotus_metadata = generate_scotus_llm_fields(
            sample_scotus_text, sample_syllabus
        )

        results["generate_scotus_llm_fields_with_syllabus"] = {
            "method": "generate_scotus_llm_fields() with syllabus",
            "result": {
                "plain_language_summary": (
                    scotus_metadata.get("plain_language_summary", "")[:200] + "..."
                    if len(scotus_metadata.get("plain_language_summary", "")) > 200
                    else scotus_metadata.get("plain_language_summary", "")
                ),
                "holding_plain": scotus_metadata.get("holding_plain", ""),
                "outcome_simple": scotus_metadata.get("outcome_simple", ""),
                "issue_plain": scotus_metadata.get("issue_plain", ""),
                "reasoning": (
                    scotus_metadata.get("reasoning", "")[:200] + "..."
                    if len(scotus_metadata.get("reasoning", "")) > 200
                    else scotus_metadata.get("reasoning", "")
                ),
                "constitution_cited": scotus_metadata.get("constitution_cited", []),
                "federal_statutes_cited": scotus_metadata.get(
                    "federal_statutes_cited", []
                ),
                "federal_regulations_cited": scotus_metadata.get(
                    "federal_regulations_cited", []
                ),
                "cases_cited": scotus_metadata.get("cases_cited", []),
                "topics_or_policy_areas": scotus_metadata.get(
                    "topics_or_policy_areas", []
                ),
            },
        }

        # Test without syllabus
        scotus_metadata_no_syllabus = generate_scotus_llm_fields(sample_scotus_text)

        results["generate_scotus_llm_fields_no_syllabus"] = {
            "method": "generate_scotus_llm_fields() without syllabus",
            "result": {
                "plain_language_summary": (
                    scotus_metadata_no_syllabus.get("plain_language_summary", "")[:200]
                    + "..."
                    if len(
                        scotus_metadata_no_syllabus.get("plain_language_summary", "")
                    )
                    > 200
                    else scotus_metadata_no_syllabus.get("plain_language_summary", "")
                ),
                "topics_count": len(
                    scotus_metadata_no_syllabus.get("topics_or_policy_areas", [])
                ),
                "total_citations": len(
                    scotus_metadata_no_syllabus.get("constitution_cited", [])
                )
                + len(scotus_metadata_no_syllabus.get("federal_statutes_cited", []))
                + len(scotus_metadata_no_syllabus.get("cases_cited", [])),
            },
        }

    except Exception as e:
        results["generate_scotus_llm_fields"] = {
            "method": "generate_scotus_llm_fields()",
            "error": str(e),
        }

    # Test generate_eo_llm_fields
    try:
        sample_eo_text = """Executive Order 14999

By the authority vested in me as President by the Constitution and the laws of the United States of America, I hereby order:

Section 1. Purpose. This order directs federal agencies to prioritize climate resilience in all infrastructure investments and to ensure that Federal investments consider climate change impacts pursuant to 42 U.S.C. § 4332.

Sec. 2. Policy. It is the policy of my Administration to ensure that Federal investments in infrastructure projects consider climate change impacts and promote sustainable development.

Sec. 3. Requirements. The Department of Transportation and the Environmental Protection Agency shall develop new guidelines for assessing climate risks in federal projects."""

        eo_metadata = generate_eo_llm_fields(sample_eo_text)

        results["generate_eo_llm_fields"] = {
            "method": "generate_eo_llm_fields()",
            "result": {
                "plain_language_summary": (
                    eo_metadata.get("plain_language_summary", "")[:200] + "..."
                    if len(eo_metadata.get("plain_language_summary", "")) > 200
                    else eo_metadata.get("plain_language_summary", "")
                ),
                "agencies_impacted": eo_metadata.get("agencies_impacted", []),
                "constitution_cited": eo_metadata.get("constitution_cited", []),
                "federal_statutes_cited": eo_metadata.get("federal_statutes_cited", []),
                "federal_regulations_cited": eo_metadata.get(
                    "federal_regulations_cited", []
                ),
                "cases_cited": eo_metadata.get("cases_cited", []),
                "topics_or_policy_areas": eo_metadata.get("topics_or_policy_areas", []),
                "summary_starts_with_action_verb": any(
                    eo_metadata.get("plain_language_summary", "").startswith(verb)
                    for verb in [
                        "Establishes",
                        "Prohibits",
                        "Requires",
                        "Revokes",
                        "Directs",
                        "Creates",
                        "Modifies",
                        "Authorizes",
                        "Mandates",
                        "Rescinds",
                    ]
                ),
            },
        }

    except Exception as e:
        results["generate_eo_llm_fields"] = {
            "method": "generate_eo_llm_fields()",
            "error": str(e),
        }

    # Print results in pretty JSON format
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
