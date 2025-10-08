"""
LLM-based metadata extraction using GPT-5-nano.

This module provides functions to extract structured document-level metadata from legal documents
using OpenAI's GPT-5-nano model. It generates technical summaries optimized for RAG retrieval,
extracts citations, and identifies key legal concepts to enhance semantic search and provide
context for understanding document chunks.

The module focuses on:
    - Document-level summaries optimized for LLM clients and semantic search
    - Structured citation extraction in Bluebook format with validation
    - Topic and policy area identification balancing technical precision and searchability
    - Supreme Court opinion analysis (holdings, outcomes, issues, reasoning)
    - Executive Order impact assessment (actions, agencies, deadlines)

Python Learning Notes:
    - OpenAI client requires API key from environment variables
    - JSON mode ensures structured output from the LLM
    - Type hints improve code clarity and IDE support
    - Exception handling ensures graceful degradation
    - Docstrings provide comprehensive documentation
"""

import json
import re
import time
from typing import Any, Dict, List, Optional

from openai import APIError, OpenAI, RateLimitError

from ..utils import get_logger
from ..utils.config import get_openai_api_key

logger = get_logger(__name__)


def generate_scotus_llm_fields(
    text: str, syllabus: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate LLM-extracted document-level metadata for Supreme Court opinions.

    This function uses GPT-5-nano to extract structured metadata that provides context for
    understanding individual chunks (500-800 token fragments) from much larger opinions (15,000+ words).
    The metadata is optimized for RAG retrieval and LLM comprehension, using precise legal terminology
    rather than simplified language.

    It prioritizes the Syllabus (when available) for extracting holdings, outcomes, and issues,
    as the Syllabus provides official summaries prepared by the Court Reporter's office.

    The function extracts:
        - Document-level technical summary (1-2 dense sentences)
        - Citations to Constitution, statutes, regulations, and cases (validated, text-backed)
        - Topics and policy areas balancing technical precision with searchability
        - Court holdings, outcomes, issues, and reasoning using legal terminology

    Syllabus Priority:
        When a Syllabus is provided, it takes precedence for extracting:
        - holding_plain: The Court's holding using precise legal terminology
        - outcome_simple: The case disposition
        - issue_plain: The central legal question

        When NO Syllabus is provided, these fields are extracted ONLY from the majority opinion
        (never from dissents or concurrences).

    Args:
        text (str): Full text of the Supreme Court opinion, including all
                   opinion types (majority, concurring, dissenting)
        syllabus (Optional[str]): The Syllabus text if available, which is
                                 the official Court summary. When provided,
                                 this is used preferentially for key fields.

    Returns:
        Dict[str, Any]: Dictionary containing extracted metadata fields:
            - document_summary: 1-2 dense, technical sentences providing document-level context
            - constitution_cited: List of constitutional citations (text-backed, validated)
            - federal_statutes_cited: List of U.S.C. citations (text-backed, validated)
            - federal_regulations_cited: List of C.F.R. citations (text-backed, validated)
            - cases_cited: List of case citations (text-backed, validated)
            - topics_or_policy_areas: 5-8 topic tags (technical + searchable)
            - holding_plain: One-sentence holding using legal terminology
            - outcome_simple: Case disposition and consequence
            - issue_plain: Central legal question
            - reasoning: Court's key reasoning (3-4 sentences)

    Example:
        # With Syllabus (preferred approach)
        opinion_text = "Full opinion text here..."
        syllabus_text = "SYLLABUS\\n\\nHeld: The Court held that..."

        metadata = generate_scotus_llm_fields(opinion_text, syllabus_text)
        print(metadata["document_summary"])  # Technical summary of entire case
        print(metadata["constitution_cited"])  # Validated citations from full opinion

        # Without Syllabus (fallback - extracts from majority only)
        metadata = generate_scotus_llm_fields(opinion_text)
        print(metadata["holding_plain"])  # From majority opinion, not dissents

    Python Learning Notes:
        - Optional parameters allow flexible function usage
        - JSON mode ensures structured LLM output
        - Exception handling provides robustness
        - Type hints clarify expected inputs and outputs
    """
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=get_openai_api_key())

        # Prepare the content for analysis
        analysis_content = text
        syllabus_instruction = ""

        if syllabus:
            # If Syllabus is available, prepend it for priority extraction
            analysis_content = f"SYLLABUS (USE THIS FOR HOLDING, OUTCOME, AND ISSUE):\n{syllabus}\n\nFULL OPINION:\n{text}"
            syllabus_instruction = """
            CRITICAL: Extract holding_plain, outcome_simple, and issue_plain ONLY from the SYLLABUS section.
            The Syllabus is the Court's official summary and provides the authoritative source for these fields.
            Use the full opinion for all other fields (citations, topics, reasoning).
            """
        else:
            syllabus_instruction = """
            CRITICAL: When NO Syllabus is provided, extract holding_plain, outcome_simple, and issue_plain
            ONLY from the majority opinion. NEVER use dissenting or concurring opinions for these fields.
            Dissents and concurrences represent alternative views, not the Court's actual holding.
            """

        # System prompt defining the extraction task
        system_prompt = f"""You are a legal analyst extracting document-level metadata from Supreme Court opinions for a RAG system.

Your task is to create metadata that provides context for understanding individual chunks (500-800 token fragments)
from much larger opinions (15,000+ words). This metadata helps LLM clients assess chunk relevance and synthesize
answers to user queries.

CRITICAL: Use precise legal terminology. Dense, technical summaries improve semantic search and provide
better context than simplified language. The LLM clients consuming this metadata will translate to plain
language for end users as needed.

{syllabus_instruction}

REASONING PROCESS - Before extracting, think through:
1. Document structure: Identify the Syllabus (if present), majority opinion, concurrences, and dissents
2. Controlling holdings: Determine what the Court actually held (majority view only)
3. Citations: Identify constitutional provisions, statutes, regulations, and cases that are actually cited verbatim
4. Key reasoning: Trace the Court's logical progression from issue to holding

OUTPUT FORMAT:
- Return ONLY a single JSON object
- NO markdown code fences (no ```json)
- NO explanatory text before or after the JSON
- NO additional commentary
- Just the raw JSON object

Expected JSON schema:
{{
  "document_summary": "string (1-2 dense sentences)",
  "constitution_cited": ["array of strings"],
  "federal_statutes_cited": ["array of strings"],
  "federal_regulations_cited": ["array of strings"],
  "cases_cited": ["array of strings"],
  "topics_or_policy_areas": ["array of 5-8 strings"],
  "holding_plain": "string",
  "outcome_simple": "string",
  "issue_plain": "string",
  "reasoning": "string"
}}

Extract the following fields in JSON format:

1. document_summary: One to two dense, technical sentences providing document-level context.
   - State the legal question, holding, and key reasoning
   - Use precise legal terminology (constitutional provisions, statutes, legal doctrines)
   - Include vote breakdown and note dissents if applicable
   - Focus on information density, not narrative flow
   - This appears with every chunk, so keep it concise (~40 words)

   Example: "Court held CFPB funding via Federal Reserve earnings satisfies Art. I, § 9, cl. 7 Appropriations Clause. Statutory authorization in 12 U.S.C. § 5497(a)(1) constitutes valid appropriation; applied rational basis review. 7-2 decision; Alito dissenting on historical practice grounds."

   NOT: "In a case about government agency funding, the Court decided that the Consumer Financial Protection Bureau can get its money from the Federal Reserve. The Court reasoned that Congress gave permission for this arrangement, which is enough under the Constitution's rules about government spending."

2. constitution_cited: Array of U.S. Constitution citations in Bluebook format.
   - ONLY include citations that appear verbatim in the provided text
   - Use proper Bluebook format with correct spacing and punctuation
   - Remove duplicates; preserve order of first appearance
   - If no constitutional citations appear, return an empty array []

   Examples:
   ✅ CORRECT: "U.S. Const. amend. XIV, § 1"
   ✅ CORRECT: "U.S. Const. art. I, § 8, cl. 3"
   ❌ INCORRECT: "14th Amendment Section 1"
   ❌ INCORRECT: "Article I Section 8"

3. federal_statutes_cited: Array of U.S.C. citations in Bluebook format.
   - ONLY include citations that appear verbatim in the provided text
   - Use proper spacing: "42 U.S.C. § 1983" (note space before §)
   - Remove duplicates; preserve order of first appearance
   - If no statute citations appear, return an empty array []

   Examples:
   ✅ CORRECT: "42 U.S.C. § 1983"
   ✅ CORRECT: "8 U.S.C. § 1182(f)"
   ❌ INCORRECT: "Section 1983"
   ❌ INCORRECT: "42 USC 1983"

4. federal_regulations_cited: Array of C.F.R. citations in Bluebook format.
   - ONLY include citations that appear verbatim in the provided text
   - Remove duplicates; preserve order of first appearance
   - If no regulation citations appear, return an empty array []

   Examples:
   ✅ CORRECT: "14 C.F.R. § 91.817"
   ❌ INCORRECT: "14 CFR 91.817"

5. cases_cited: Array of case citations in Bluebook format.
   - ONLY include citations that appear verbatim in the provided text
   - Include case name, reporter, and year
   - Remove duplicates; preserve order of first appearance
   - If no case citations appear, return an empty array []

   Examples:
   ✅ CORRECT: "Brown v. Bd. of Educ., 347 U.S. 483 (1954)"
   ✅ CORRECT: "Chevron U.S.A. Inc. v. NRDC, 467 U.S. 837 (1984)"
   ❌ INCORRECT: "Brown v. Board of Education"
   ❌ INCORRECT: "the Chevron case"

6. topics_or_policy_areas: Array of 5-8 tags balancing technical precision with searchability.
   - Include THREE types of tags:
     * Broad policy areas: "environmental law", "healthcare", "criminal procedure"
     * Specific legal doctrines: "Chevron deference", "qualified immunity", "Commerce Clause", "Appropriations Clause"
     * Affected entities/areas: "federal agencies", "state governments", "individual rights", "regulatory authority"
   - Remove duplicates; preserve order of appearance
   - Return exactly 5-8 tags (no more, no fewer)

   Good examples: ["administrative law", "Chevron deference", "EPA rulemaking", "Clean Air Act", "statutory interpretation", "federal agencies"]
   Bad examples: ["constitutional law", "legal case", "court decision"] (too generic)

7. holding_plain: The Court's holding in ONE clear, declarative sentence.
   - State what the Court held using precise legal terminology
   - Focus on the substantive legal determination
   - Example: "Statutory authorization of CFPB funding satisfies the Appropriations Clause"
   - Example: "Fourth Amendment requires warrant for cell phone searches incident to arrest"

8. outcome_simple: The case disposition and its immediate consequence.
   - State the procedural outcome (affirmed, reversed, vacated, remanded)
   - Note what happens next if applicable
   - Example: "Affirmed lower court judgment upholding CFPB funding mechanism"
   - Example: "Reversed Ninth Circuit and remanded for reconsideration under strict scrutiny"

9. issue_plain: The central legal question before the Court.
   - Frame as a question using legal terminology
   - Be specific about the constitutional/statutory provision at issue
   - Example: "Whether CFPB funding via Federal Reserve earnings violates Art. I, § 9, cl. 7 Appropriations Clause"
   - Example: "Whether search-incident-to-arrest exception applies to digital devices under Fourth Amendment"

10. reasoning: The Court's key reasoning in one concise paragraph (3-4 sentences).
    - State the legal standard or test applied
    - Explain the Court's analytical framework
    - Note key precedents relied upon or distinguished
    - Use precise legal terminology

    Example: "Applied rational basis review to appropriations challenges. Statutory authorization constitutes valid appropriation under historical practice dating to founding era. Distinguished from nondelegation doctrine cases where Congress delegates legislative power rather than authorizing expenditures. Relied on precedent upholding standing appropriations for judicial salaries and mint operations."
"""

        # User prompt with the opinion text
        user_prompt = (
            f"Extract metadata from this Supreme Court opinion:\n\n{analysis_content}"
        )

        # Call GPT-5-mini with JSON response format and retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_completion_tokens=2000,
                    reasoning_effort="minimal",
                )
                break  # Success, exit retry loop
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        "Rate limited on attempt %d/%d, waiting %ds: %s",
                        attempt + 1,
                        max_retries,
                        wait_time,
                        str(e),
                    )
                    time.sleep(wait_time)
                    continue
                raise  # Re-raise on final attempt
            except APIError as e:
                if (
                    attempt < max_retries - 1
                    and hasattr(e, "status_code")
                    and e.status_code in [502, 503, 504]
                ):
                    wait_time = 2**attempt
                    logger.warning(
                        "API error %d on attempt %d/%d, waiting %ds: %s",
                        e.status_code,
                        attempt + 1,
                        max_retries,
                        wait_time,
                        str(e),
                    )
                    time.sleep(wait_time)
                    continue
                raise  # Re-raise on final attempt or non-retryable errors

        # Log finish_reason and refusal for debugging content filter issues
        logger.info(f"Finish reason: {response.choices[0].finish_reason}")
        logger.info(f"Refusal: {response.choices[0].message.refusal}")

        # Check if response has content
        if not response.choices or not response.choices[0].message.content:
            logger.error("Empty response from OpenAI API for SCOTUS metadata")
            raise ValueError("Empty response from OpenAI API")

        # Parse the JSON response
        response_content = response.choices[0].message.content
        logger.debug("OpenAI response length: %d characters", len(response_content))

        try:
            result = json.loads(response_content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse OpenAI JSON response: %s", str(e))
            logger.debug(
                "Response content: %s", response_content[:500]
            )  # Log first 500 chars
            raise

        # Ensure all required fields are present with defaults
        required_fields = {
            "document_summary": "",
            "constitution_cited": [],
            "federal_statutes_cited": [],
            "federal_regulations_cited": [],
            "cases_cited": [],
            "topics_or_policy_areas": [],
            "holding_plain": "",
            "outcome_simple": "",
            "issue_plain": "",
            "reasoning": "",
        }

        # Merge with defaults to ensure all fields exist
        for field, default in required_fields.items():
            if field not in result:
                result[field] = default

        # Validate topics count (ensure 5-8 topics)
        if len(result["topics_or_policy_areas"]) < 5:
            logger.warning("Less than 5 topics extracted, may affect retrieval quality")
        elif len(result["topics_or_policy_areas"]) > 8:
            result["topics_or_policy_areas"] = result["topics_or_policy_areas"][:8]

        logger.debug(
            "Successfully extracted SCOTUS metadata with %d citations",
            sum(
                len(result[f])
                for f in [
                    "constitution_cited",
                    "federal_statutes_cited",
                    "federal_regulations_cited",
                    "cases_cited",
                ]
            ),
        )

        return result

    except Exception as e:
        logger.error("Failed to extract SCOTUS metadata: %s", str(e), exc_info=True)
        # Return minimal valid metadata on error
        return {
            "document_summary": "Unable to generate summary.",
            "constitution_cited": [],
            "federal_statutes_cited": [],
            "federal_regulations_cited": [],
            "cases_cited": [],
            "topics_or_policy_areas": ["legal", "court decision"],
            "holding_plain": "Unable to extract holding.",
            "outcome_simple": "Unable to determine outcome.",
            "issue_plain": "Unable to extract issue.",
            "reasoning": "Unable to extract reasoning.",
        }


def generate_eo_llm_fields(text: str) -> Dict[str, Any]:
    """
    Generate LLM-extracted document-level metadata for Executive Orders.

    This function uses GPT-5-nano to extract structured metadata that provides context for
    understanding individual chunks (300-400 token fragments) from Executive Orders. The metadata
    is optimized for RAG retrieval and LLM comprehension, using precise policy and legal terminology.

    The function extracts:
        - Document-level technical summary (1-2 dense sentences)
        - Impacted federal agencies with canonical names
        - Citations to Constitution, statutes, regulations (validated, text-backed)
        - Policy areas and topics balancing technical precision with searchability

    Executive Order Specifics:
        - Summaries include specific agency names, CFR/USC citations, and deadlines
        - Agency identification uses full canonical names
        - Topics cover policy areas, mechanisms, and affected sectors
        - All citations must appear verbatim in the order text

    Args:
        text (str): Full text of the Executive Order, including all sections
                   and subsections. Should be the cleaned text from the
                   Federal Register API.

    Returns:
        Dict[str, Any]: Dictionary containing extracted metadata fields:
            - document_summary: 1-2 dense, technical sentences providing document-level context
            - agencies_impacted: List of federal agencies (canonical names, deduplicated)
            - constitution_cited: List of constitutional citations (text-backed, validated)
            - federal_statutes_cited: List of U.S.C. citations (text-backed, validated)
            - federal_regulations_cited: List of C.F.R. citations (text-backed, validated)
            - cases_cited: List of case citations (text-backed, validated)
            - topics_or_policy_areas: 5-8 topic tags (technical + searchable)

    Example:
        eo_text = "Executive Order 14304\\n\\nSec. 1. Purpose..."

        metadata = generate_eo_llm_fields(eo_text)
        print(metadata["document_summary"])
        # "Directs FAA to repeal 14 C.F.R. § 91.817 supersonic flight ban within 180 days..."

        print(metadata["agencies_impacted"])
        # ["Federal Aviation Administration", "Department of Transportation", "Office of Science and Technology Policy"]

    Python Learning Notes:
        - JSON response format ensures structured output
        - Reasoning instructions improve extraction accuracy
        - Default values prevent missing field errors
        - Logging helps with debugging and monitoring
    """
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=get_openai_api_key())

        # System prompt defining the extraction task for Executive Orders
        system_prompt = """You are a policy analyst extracting document-level metadata from Presidential Executive Orders for a RAG system.

Your task is to create metadata that provides context for understanding individual chunks (300-400 token fragments)
from much larger executive orders. This metadata helps LLM clients assess chunk relevance and synthesize answers
to user queries.

CRITICAL: Use precise policy and legal terminology. Include specific agency names, statutory citations, and
regulatory mechanisms. The LLM clients consuming this metadata will translate to accessible language for end
users as needed.

REASONING PROCESS - Before extracting, think through:
1. Document structure: Identify header, sections, subsections, and signature block
2. Key actions: What does this order mandate, prohibit, establish, or revoke?
3. Affected entities: Which agencies must take action? Which are affected?
4. Legal authorities: Identify constitutional provisions, statutes, and regulations that are actually cited verbatim
5. Deadlines: Note any explicit timelines or effective dates mentioned in the text

OUTPUT FORMAT:
- Return ONLY a single JSON object
- NO markdown code fences (no ```json)
- NO explanatory text before or after the JSON
- NO additional commentary
- Just the raw JSON object

Expected JSON schema:
{{
  "document_summary": "string (1-2 dense sentences)",
  "agencies_impacted": ["array of strings"],
  "constitution_cited": ["array of strings"],
  "federal_statutes_cited": ["array of strings"],
  "federal_regulations_cited": ["array of strings"],
  "cases_cited": ["array of strings"],
  "topics_or_policy_areas": ["array of 5-8 strings"]
}}

Extract the following fields in JSON format:

1. document_summary: One to two dense, technical sentences providing document-level context.
   - State the order's key mandates, prohibitions, or establishments
   - Include specific agency names, CFR/USC citations, and deadlines
   - Use precise policy terminology and regulatory mechanisms
   - Focus on information density, not accessibility
   - This appears with every chunk, so keep it concise (~40 words)

   Example: "Directs FAA to repeal 14 C.F.R. § 91.817 supersonic flight ban within 180 days and establish noise-based certification under 14 C.F.R. Part 36. Coordinates supersonic R&D through OSTP with DOD, DOC, DOT, and NASA participation; mandates NPRM within 18 months."

   NOT: "Creates a new task force within the Department of Transportation to speed up approval of supersonic aircraft for commercial flights. This aims to make supersonic passenger travel available in the United States by reducing regulatory delays. The order affects aircraft manufacturers, airlines planning supersonic routes, and the Federal Aviation Administration, which must update its rules within 180 days."

2. agencies_impacted: Array of federal agencies that must take action or are affected by this order.
   - Use full, canonical department names: "Department of Transportation", "Environmental Protection Agency"
   - Expand acronyms on first mention when helpful: "Federal Aviation Administration (FAA)"
   - Include both primary agencies (who must act) and secondary agencies (who are affected)
   - Remove duplicates; preserve order of first appearance
   - Avoid listing the same agency multiple times with different names

3. constitution_cited: Array of U.S. Constitution citations in Bluebook format.
   - ONLY include citations that appear verbatim in the provided text
   - Remove duplicates; preserve order of first appearance
   - If no constitutional citations appear, return an empty array []

4. federal_statutes_cited: Array of U.S.C. citations in Bluebook format.
   - ONLY include citations that appear verbatim in the provided text
   - Use proper spacing: "42 U.S.C. § 4332" (note space before §)
   - Remove duplicates; preserve order of first appearance
   - If no statute citations appear, return an empty array []

5. federal_regulations_cited: Array of C.F.R. citations in Bluebook format.
   - ONLY include citations that appear verbatim in the provided text
   - Remove duplicates; preserve order of first appearance
   - If no regulation citations appear, return an empty array []

6. cases_cited: Array of case citations in Bluebook format (rare in EOs but possible).
   - ONLY include citations that appear verbatim in the provided text
   - Remove duplicates; preserve order of first appearance
   - If no case citations appear, return an empty array []

7. topics_or_policy_areas: Array of 5-8 tags using terms regular people would search for.

   Include a mix across three categories:
   - Broad policy areas: "climate change", "national security", "healthcare", "immigration"
   - Specific topics/mechanisms: "electric vehicles", "border security", "prescription drugs", "regulatory reform"
   - Affected sectors: "small business", "farming", "technology", "manufacturing"

   Remove duplicates; preserve order of appearance
   Return exactly 5-8 tags (no more, no fewer)
   ONLY include topics based on what is actually in the order text (do not speculate about community impacts)

   Good examples: ["clean energy", "electric vehicles", "auto industry", "climate change", "manufacturing jobs"]
   Bad examples: ["regulatory reform", "administrative procedure", "executive authority", "federal policy"] (too generic)

   Think: "What would someone type into a search engine to find this order?"
"""

        # User prompt with the Executive Order text
        user_prompt = f"Extract metadata from this Executive Order:\n\n{text}"

        # Call GPT-5-mini with JSON response format and retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_completion_tokens=1500,
                    reasoning_effort="minimal",
                )
                break  # Success, exit retry loop
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        "Rate limited on attempt %d/%d, waiting %ds: %s",
                        attempt + 1,
                        max_retries,
                        wait_time,
                        str(e),
                    )
                    time.sleep(wait_time)
                    continue
                raise  # Re-raise on final attempt
            except APIError as e:
                if (
                    attempt < max_retries - 1
                    and hasattr(e, "status_code")
                    and e.status_code in [502, 503, 504]
                ):
                    wait_time = 2**attempt
                    logger.warning(
                        "API error %d on attempt %d/%d, waiting %ds: %s",
                        e.status_code,
                        attempt + 1,
                        max_retries,
                        wait_time,
                        str(e),
                    )
                    time.sleep(wait_time)
                    continue
                raise  # Re-raise on final attempt or non-retryable errors

        # Log finish_reason and refusal for debugging content filter issues
        logger.info(f"Finish reason: {response.choices[0].finish_reason}")
        logger.info(f"Refusal: {response.choices[0].message.refusal}")

        # Check if response has content
        if not response.choices or not response.choices[0].message.content:
            logger.error("Empty response from OpenAI API for EO metadata")
            raise ValueError("Empty response from OpenAI API")

        # Parse the JSON response
        response_content = response.choices[0].message.content
        logger.debug("OpenAI response length: %d characters", len(response_content))

        try:
            result = json.loads(response_content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse OpenAI JSON response: %s", str(e))
            logger.debug(
                "Response content: %s", response_content[:500]
            )  # Log first 500 chars
            raise

        # Ensure all required fields are present with defaults
        required_fields = {
            "document_summary": "",
            "agencies_impacted": [],
            "constitution_cited": [],
            "federal_statutes_cited": [],
            "federal_regulations_cited": [],
            "cases_cited": [],
            "topics_or_policy_areas": [],
        }

        # Merge with defaults to ensure all fields exist
        for field, default in required_fields.items():
            if field not in result:
                result[field] = default

        # Validate and adjust topics count (ensure 5-8 topics)
        if len(result["topics_or_policy_areas"]) < 5:
            # Add generic topics if too few
            generic_topics = [
                "federal policy",
                "executive action",
                "government regulation",
            ]
            while len(result["topics_or_policy_areas"]) < 5 and generic_topics:
                if generic_topics[0] not in result["topics_or_policy_areas"]:
                    result["topics_or_policy_areas"].append(generic_topics.pop(0))
        elif len(result["topics_or_policy_areas"]) > 8:
            result["topics_or_policy_areas"] = result["topics_or_policy_areas"][:8]

        logger.debug(
            "Successfully extracted EO metadata with %d impacted agencies",
            len(result["agencies_impacted"]),
        )

        return result

    except Exception as e:
        logger.error(
            "Failed to extract Executive Order metadata: %s", str(e), exc_info=True
        )
        # Return minimal valid metadata on error
        return {
            "document_summary": "Unable to generate summary.",
            "agencies_impacted": [],
            "constitution_cited": [],
            "federal_statutes_cited": [],
            "federal_regulations_cited": [],
            "cases_cited": [],
            "topics_or_policy_areas": ["federal policy", "executive action"],
        }


# Docstring examples for testing
if __name__ == "__main__":
    """
    Minimal examples demonstrating LLM extraction functionality.

    These examples show how the extraction functions work with sample text.
    In production, these functions are called by build_payloads.py with
    real document text from government APIs.
    """

    # Example SCOTUS opinion with Syllabus
    sample_scotus = """
    SYLLABUS

    Held: The Fourth Amendment requires police to obtain a warrant before
    conducting a search of digital devices seized incident to arrest.

    The Court reasoned that digital devices differ from physical objects due to
    their immense storage capacity and the breadth of private information they contain.

    JUSTICE ROBERTS delivered the opinion of the Court.

    The question presented is whether the police may, without a warrant, search
    digital information on a cell phone seized from an individual who has been arrested.
    """

    sample_syllabus = """
    Held: The Fourth Amendment requires police to obtain a warrant before
    conducting a search of digital devices seized incident to arrest.
    """

    # Test SCOTUS extraction
    print("Testing SCOTUS extraction with Syllabus...")
    try:
        scotus_metadata = generate_scotus_llm_fields(sample_scotus, sample_syllabus)
        print(f"Holding: {scotus_metadata['holding_plain']}")
        print(f"Topics: {scotus_metadata['topics_or_policy_areas']}")
    except Exception as e:
        print(f"Error: {e}")

    # Example Executive Order
    sample_eo = """
    Executive Order 14999

    Section 1. Purpose. This order directs federal agencies to prioritize
    climate resilience in all infrastructure investments.

    Sec. 2. Policy. It is the policy of my Administration to ensure that
    Federal investments in infrastructure projects consider climate change impacts.

    Sec. 3. Requirements. The Department of Transportation shall develop new
    guidelines pursuant to 42 U.S.C. § 4332 for assessing climate risks.
    """

    # Test EO extraction
    print("\nTesting Executive Order extraction...")
    try:
        eo_metadata = generate_eo_llm_fields(sample_eo)
        print(f"Summary: {eo_metadata['plain_language_summary']}")
        print(f"Agencies: {eo_metadata['agencies_impacted']}")
    except Exception as e:
        print(f"Error: {e}")
