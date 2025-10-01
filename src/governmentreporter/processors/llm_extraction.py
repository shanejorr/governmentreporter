"""
LLM-based metadata extraction using GPT-5-nano.

This module provides functions to extract structured metadata from legal documents
using OpenAI's GPT-5-nano model. It generates plain-language summaries, extracts
citations, and identifies key legal concepts to enhance retrieval capabilities.

The module focuses on:
    - Plain-language explanations for lay users
    - Structured citation extraction in Bluebook format
    - Topic and policy area identification
    - Supreme Court opinion analysis (holdings, outcomes, issues)
    - Executive Order impact assessment

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

from openai import OpenAI, RateLimitError, APIError

from ..utils import get_logger
from ..utils.config import get_openai_api_key

logger = get_logger(__name__)


def generate_scotus_llm_fields(
    text: str, syllabus: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate LLM-extracted metadata fields for Supreme Court opinions.

    This function uses GPT-5-nano to extract structured metadata from Supreme Court
    opinion text. It prioritizes the Syllabus (when available) for extracting
    holdings, outcomes, and issues, as the Syllabus provides official summaries
    prepared by the Court Reporter's office.

    The function extracts:
        - Plain-language legal summaries and explanations
        - Citations to Constitution, statutes, regulations, and cases
        - Topics and policy areas for improved retrieval
        - Court holdings, outcomes, issues, and reasoning

    Syllabus Priority:
        When a Syllabus is provided, it takes precedence for extracting:
        - holding_plain: The Court's holding in one sentence
        - outcome_simple: The case outcome in simple terms
        - issue_plain: The central legal question
        The Syllabus is the Court's official summary and provides the most
        authoritative source for these key elements.

    Args:
        text (str): Full text of the Supreme Court opinion, including all
                   opinion types (majority, concurring, dissenting)
        syllabus (Optional[str]): The Syllabus text if available, which is
                                 the official Court summary. When provided,
                                 this is used preferentially for key fields.

    Returns:
        Dict[str, Any]: Dictionary containing extracted metadata fields:
            - plain_language_summary: One-paragraph summary using the template
              "The Court held [holding]... It stated... [reasoning]."
            - constitution_cited: List of constitutional citations
            - federal_statutes_cited: List of U.S.C. citations
            - federal_regulations_cited: List of C.F.R. citations
            - cases_cited: List of case citations with names and reporters
            - topics_or_policy_areas: 5-8 topic tags
            - holding_plain: One-sentence holding statement
            - outcome_simple: Simple outcome description
            - issue_plain: Central question in plain English
            - reasoning: Court's reasoning in one paragraph

    Example:
        # With Syllabus (preferred approach)
        opinion_text = "Full opinion text here..."
        syllabus_text = "SYLLABUS\\n\\nHeld: The Court held that..."

        metadata = generate_scotus_llm_fields(opinion_text, syllabus_text)
        print(metadata["holding_plain"])  # Extracted from Syllabus
        print(metadata["constitution_cited"])  # From full opinion

        # Without Syllabus (fallback)
        metadata = generate_scotus_llm_fields(opinion_text)
        print(metadata["issue_plain"])  # Extracted from opinion text

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
            IMPORTANT: Extract holding_plain, outcome_simple, and issue_plain ONLY from the SYLLABUS section.
            The Syllabus is the authoritative summary. Use the full opinion for all other fields.
            """

        # System prompt defining the extraction task
        system_prompt = f"""You are a legal analyst extracting metadata from Supreme Court opinions for a RAG system.
Your task is to extract structured metadata that helps lay users (non-lawyers) understand complex legal documents.

CRITICAL: Use simple, everyday language. Avoid legal jargon at all costs.

{syllabus_instruction}

Extract the following fields in JSON format:

1. plain_language_summary: One paragraph following this structure:
   - Start with: "In a case about [what the case is about in everyday terms]..."
   - Then: "the Court decided that [holding in plain English]."
   - Finally: "The Court reasoned that [why they decided this way - the key reason]."

   Example: "In a case about whether police can search someone's phone without a warrant, the Court decided that police must get a warrant before searching digital devices. The Court reasoned that cell phones contain massive amounts of private information that deserves strong privacy protection."

2. constitution_cited: Array of U.S. Constitution citations in Bluebook format (e.g., "U.S. Const. amend. XIV, § 1", "U.S. Const. art. I, § 8, cl. 3")

3. federal_statutes_cited: Array of U.S.C. citations in Bluebook format (e.g., "42 U.S.C. § 1983", "8 U.S.C. § 1182(f)")

4. federal_regulations_cited: Array of C.F.R. citations in Bluebook format (e.g., "14 C.F.R. § 91.817")

5. cases_cited: Array of case citations in Bluebook format (e.g., "Brown v. Bd. of Educ., 347 U.S. 483 (1954)")

6. topics_or_policy_areas: Array of 5-8 tags that mix legal concepts AND everyday search terms people might use.
   - Include both: technical legal terms (e.g., "due process", "commerce clause")
   - AND everyday topics (e.g., "healthcare", "voting rights", "police searches", "religious freedom")
   - Think: "What would a regular person search for to find this case?"
   - Good examples: ["abortion rights", "religious freedom", "healthcare law", "federal power"]
   - Bad examples: ["constitutional law", "statutory interpretation", "judicial review"]

7. holding_plain: The Court's decision in ONE sentence using simple language.
   - Avoid legal jargon. Instead of "petitioner prevailed" say "the person who sued won"
   - Instead of "reversed and remanded" say "overturned the lower court's decision and sent it back"
   - Focus on WHAT the Court decided, not the technical legal outcome

8. outcome_simple: Who won and what happens next, in simple terms.
   - Instead of: "Reversed and remanded"
   - Say: "The person who sued won. The case goes back to the lower court for a new decision."
   - Instead of: "Affirmed"
   - Say: "The lower court's decision stands. The person who appealed lost."

9. issue_plain: The central question the Court answered, phrased as a simple question anyone could understand.
   - Start with: "Can...", "Does...", "Must...", "Is it constitutional to..."
   - Example: "Can Congress pass a law requiring people to buy health insurance?"
   - NOT: "Whether the Affordable Care Act's individual mandate exceeds Congress's enumerated powers"

10. reasoning: Why did the Court decide this way? Explain in ONE paragraph using everyday language.
    - Focus on the Court's main reason, not all arguments
    - Explain it like you're telling a friend who knows nothing about law
    - Connect the reasoning to common sense or familiar principles when possible
    - Avoid terms like: "petitioner", "respondent", "appellant", "appellee", "certiorari", "standing", "justiciability"

FORBIDDEN LEGAL JARGON - Use these plain alternatives:
- "Petitioner" → "the person/party who sued" or "the person who appealed"
- "Respondent" → "the other party" or "the government" or "[specific party name]"
- "Affirmed" → "upheld the lower court's decision" or "kept the decision in place"
- "Reversed" → "overturned the lower court's decision"
- "Remanded" → "sent back to the lower court"
- "Reversed and remanded" → "overturned the decision and sent it back for reconsideration"
- "Vacated" → "threw out the lower court's decision"
- "Standing" → "the right to sue" or "legal permission to bring the case"
- "Certiorari" → "agreed to hear the case" or "took the case"
- "En banc" → "full court" or "all the judges"
- "Per curiam" → "unsigned opinion" or "opinion by the whole court"
- "Dicta" → "additional comments" or "side remarks"

Remember: Write for someone with NO legal training. Use concrete examples and simple explanations."""

        # User prompt with the opinion text
        user_prompt = (
            f"Extract metadata from this Supreme Court opinion:\n\n{analysis_content}"
        )

        # Call GPT-5-nano with JSON response format and retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-5-nano",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    reasoning_effort="low",  # GPT-5-nano requires this parameter
                    max_completion_tokens=2000,
                )
                break  # Success, exit retry loop
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        "Rate limited on attempt %d/%d, waiting %ds: %s",
                        attempt + 1, max_retries, wait_time, str(e)
                    )
                    time.sleep(wait_time)
                    continue
                raise  # Re-raise on final attempt
            except APIError as e:
                if attempt < max_retries - 1 and hasattr(e, 'status_code') and e.status_code in [502, 503, 504]:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "API error %d on attempt %d/%d, waiting %ds: %s",
                        e.status_code, attempt + 1, max_retries, wait_time, str(e)
                    )
                    time.sleep(wait_time)
                    continue
                raise  # Re-raise on final attempt or non-retryable errors

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
            logger.debug("Response content: %s", response_content[:500])  # Log first 500 chars
            raise

        # Ensure all required fields are present with defaults
        required_fields = {
            "plain_language_summary": "",
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
            "plain_language_summary": "Unable to generate summary.",
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
    Generate LLM-extracted metadata fields for Executive Orders.

    This function uses GPT-5-nano to extract structured metadata from Executive
    Order text. It focuses on action-oriented summaries and regulatory impacts
    to help users understand what the order does and who it affects.

    The function extracts:
        - Action-oriented plain language summary
        - Impacted federal agencies
        - Citations to Constitution, statutes, regulations, and cases
        - Policy areas and topics for improved retrieval

    Executive Order Specifics:
        - Summaries emphasize concrete actions (prohibits, requires, establishes)
        - Agency identification focuses on operational impacts
        - Topics include both policy areas and regulatory domains

    Args:
        text (str): Full text of the Executive Order, including all sections
                   and subsections. Should be the cleaned text from the
                   Federal Register API.

    Returns:
        Dict[str, Any]: Dictionary containing extracted metadata fields:
            - plain_language_summary: Action-oriented paragraph starting with
              strong verbs (establishes, prohibits, requires, revokes)
            - agencies_impacted: List of federal agencies affected by the order
            - constitution_cited: List of constitutional citations
            - federal_statutes_cited: List of U.S.C. citations
            - federal_regulations_cited: List of C.F.R. citations
            - cases_cited: List of case citations
            - topics_or_policy_areas: 5-8 topic tags

    Example:
        eo_text = "Executive Order 14304\\n\\nSec. 1. Purpose..."

        metadata = generate_eo_llm_fields(eo_text)
        print(metadata["plain_language_summary"])
        # "Establishes new requirements for federal agencies to..."

        print(metadata["agencies_impacted"])
        # ["Department of Transportation", "Federal Aviation Administration"]

    Python Learning Notes:
        - JSON response format ensures structured output
        - Low temperature (0.2) improves consistency
        - Default values prevent missing field errors
        - Logging helps with debugging and monitoring
    """
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=get_openai_api_key())

        # System prompt defining the extraction task for Executive Orders
        system_prompt = """You are a policy analyst extracting metadata from Presidential Executive Orders for a RAG system.
Your task is to extract structured metadata that helps lay users (non-lawyers, everyday Americans) understand government actions and policies.

CRITICAL: Write for regular people, not policy experts. Focus on real-world impacts.

Extract the following fields in JSON format:

1. plain_language_summary: One paragraph (3-4 sentences) explaining what this order does and who it affects.

   Structure:
   - First sentence: Start with an action verb describing what the order does
   - Second sentence: Explain the practical impact or real-world change
   - Third sentence: Note who is affected (businesses, individuals, agencies, etc.)
   - Optional fourth sentence: Mention any deadlines or implementation timeline

   Strong action verbs to use:
   - "Creates..." - for new programs, agencies, or initiatives
   - "Bans..." or "Prohibits..." - for restrictions (be specific about what's banned)
   - "Requires..." or "Mandates..." - for new obligations (explain who must do what)
   - "Cancels..." or "Eliminates..." - for ending existing programs/policies
   - "Orders [agency] to..." - when directing specific agency actions
   - "Speeds up..." - for acceleration of existing processes
   - "Protects..." - for safeguarding people or resources
   - "Expands..." - for growing existing programs

   Example: "Creates a new task force within the Department of Transportation to speed up approval of supersonic aircraft for commercial flights. This aims to make supersonic passenger travel available in the United States by reducing regulatory delays. The order affects aircraft manufacturers, airlines planning supersonic routes, and the Federal Aviation Administration, which must update its rules within 180 days."

   NOT: "Establishes interagency coordination mechanisms to facilitate regulatory harmonization for next-generation aviation technologies."

2. agencies_impacted: Array of federal agencies that must take action or are affected by this order.
   - Use full, recognizable names: "Department of Transportation", "Environmental Protection Agency"
   - Include both primary agencies (who must act) and secondary agencies (who are affected)
   - When helpful for understanding, you may note their role: "Department of Energy (renewable energy programs)"

3. constitution_cited: Array of U.S. Constitution citations in Bluebook format

4. federal_statutes_cited: Array of U.S.C. citations in Bluebook format

5. federal_regulations_cited: Array of C.F.R. citations in Bluebook format

6. cases_cited: Array of case citations in Bluebook format (rare in EOs but possible)

7. topics_or_policy_areas: Array of 5-8 tags using terms regular people would search for.

   Include a mix of:
   - Broad policy areas: "climate change", "national security", "healthcare", "immigration"
   - Specific topics: "electric vehicles", "border security", "prescription drugs", "voting access"
   - Affected sectors: "small business", "farming", "technology", "manufacturing"
   - Geographic relevance when applicable: "federal lands", "coastal areas", "tribal lands"

   Good examples: ["clean energy", "electric vehicles", "auto industry", "climate change", "manufacturing jobs"]
   Bad examples: ["regulatory reform", "administrative procedure", "executive authority", "federal policy"]

   Think: "What would someone type into a search engine to find this order?"

REMEMBER:
- Avoid bureaucratic language and acronyms without explanation
- Focus on "who does what" and "who is affected"
- Explain the practical, real-world impact
- Use concrete, specific terms over abstract policy language
- Write like you're explaining this to a friend or family member who doesn't work in government"""

        # User prompt with the Executive Order text
        user_prompt = f"Extract metadata from this Executive Order:\n\n{text}"

        # Call GPT-5-nano with JSON response format and retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-5-nano",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    reasoning_effort="low",  # GPT-5-nano requires this parameter
                    max_completion_tokens=1500,
                )
                break  # Success, exit retry loop
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        "Rate limited on attempt %d/%d, waiting %ds: %s",
                        attempt + 1, max_retries, wait_time, str(e)
                    )
                    time.sleep(wait_time)
                    continue
                raise  # Re-raise on final attempt
            except APIError as e:
                if attempt < max_retries - 1 and hasattr(e, 'status_code') and e.status_code in [502, 503, 504]:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "API error %d on attempt %d/%d, waiting %ds: %s",
                        e.status_code, attempt + 1, max_retries, wait_time, str(e)
                    )
                    time.sleep(wait_time)
                    continue
                raise  # Re-raise on final attempt or non-retryable errors

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
            logger.debug("Response content: %s", response_content[:500])  # Log first 500 chars
            raise

        # Ensure all required fields are present with defaults
        required_fields = {
            "plain_language_summary": "",
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

        # Ensure summary starts with action verb if possible
        summary = result.get("plain_language_summary", "")
        action_verbs = [
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
        if summary and not any(summary.startswith(verb) for verb in action_verbs):
            logger.warning("Executive Order summary doesn't start with action verb")

        logger.debug(
            "Successfully extracted EO metadata with %d impacted agencies",
            len(result["agencies_impacted"]),
        )

        return result

    except Exception as e:
        logger.error("Failed to extract Executive Order metadata: %s", str(e), exc_info=True)
        # Return minimal valid metadata on error
        return {
            "plain_language_summary": "Unable to generate summary.",
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
