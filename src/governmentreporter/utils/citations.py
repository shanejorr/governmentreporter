"""Bluebook citation formatting utilities.

This module provides utilities for formatting legal citations according to the
Bluebook citation style, which is the standard for legal writing in the United States.
The Bluebook (officially "The Bluebook: A Uniform System of Citation") provides
rules for citing legal authorities in academic and professional legal documents.

The module handles various types of legal citations:
    - Court case citations: "Volume Reporter Page (Year)" (e.g., "601 U.S. 416 (2024)")
    - Federal regulations: "Title C.F.R. § Section (Year)" (e.g., "14 C.F.R. § 91.817 (2025)")
    - Federal statutes: "Title U.S.C. § Section (Year)" (e.g., "12 U.S.C. § 5497 (2018)")
    - U.S. Constitution: "U.S. Const. art. Article, § Section" (e.g., "U.S. Const. art. I, § 9, cl. 7")

Integration with GovernmentReporter:
    This module supports the citation needs of the legal research system:
    - Creates standardized citations for federal regulations
    - Generates proper statute citations
    - Formats constitutional references
    - Parses citations from text for extraction and analysis
    - Supports academic and professional legal research workflows
    - Ensures consistency in legal reference formatting

Bluebook Citation Types Explained:
    1. Case Citations:
       - Volume: The volume number of the reporter series
       - Reporter: The abbreviated name of the publication (e.g., "U.S." for United States Reports)
       - Page: The page number where the case begins
       - Year: The year the case was decided (in parentheses)
       Example: "410 U.S. 113 (1973)"

    2. Federal Regulation Citations:
       - Title: The title number of the Code of Federal Regulations
       - C.F.R.: The standard abbreviation for Code of Federal Regulations
       - Section: The specific section number
       - Year: The year of the regulation edition (in parentheses)
       Example: "14 C.F.R. § 91.817 (2025)"

    3. Federal Statute Citations:
       - Title: The title number of the United States Code
       - U.S.C.: The standard abbreviation for United States Code
       - Section: The specific section number
       - Year: The year of the code edition (in parentheses)
       Example: "42 U.S.C. § 1983 (2018)"

    4. Constitutional Citations:
       - U.S. Const.: The standard abbreviation for United States Constitution
       - Article/Amendment: The article number or amendment number
       - Section: The section within the article/amendment
       - Clause: The specific clause (if applicable)
       Example: "U.S. Const. art. I, § 9, cl. 7" or "U.S. Const. amend. XIV, § 2"

Python Learning Notes:
    - Dict[str, Any] type hint indicates a dictionary with string keys and any value types
    - Optional[str] return type means the function can return a string or None
    - The .get() method safely accesses dictionary keys without KeyError exceptions
    - String splitting and list indexing are used for date parsing
    - Regular expressions (re module) are used for pattern matching in text
"""

import re
from typing import Any, Dict, Optional



def format_cfr_citation(title: str, section: str, year: Optional[str] = None) -> str:
    """Format a Code of Federal Regulations (CFR) citation in Bluebook style.

    This function creates properly formatted citations for federal regulations
    according to Bluebook rules. CFR citations are commonly found in executive
    orders, agency decisions, and regulatory documents.

    The Code of Federal Regulations (CFR) is the codification of the general
    and permanent rules published in the Federal Register by the executive
    departments and agencies of the federal government. It is divided into
    50 titles that represent broad areas subject to federal regulation.

    CFR Citation Components:
        - Title: The title number (1-50) representing the subject area
        - Section: The specific regulation section number
        - Year: The year of the CFR edition being cited (optional)

    Common CFR Titles:
        - Title 14: Aeronautics and Space
        - Title 21: Food and Drugs
        - Title 26: Internal Revenue
        - Title 42: Public Health
        - Title 49: Transportation

    Python Learning Notes:
        - The function uses default parameter values (year=None)
        - f-strings allow conditional formatting with inline expressions
        - The walrus operator could be used here but we keep it simple

    Args:
        title (str): The title number of the CFR (e.g., "14" for aeronautics).
        section (str): The section number (e.g., "91.817" for a specific rule).
            Can include subsections like "91.817(a)(1)".
        year (Optional[str]): The year of the CFR edition. If None, no year
            is included in the citation. Defaults to None.

    Returns:
        str: A properly formatted CFR citation in Bluebook style.
            Format: "Title C.F.R. § Section (Year)" if year is provided,
            or "Title C.F.R. § Section" if year is not provided.

    Example Usage:
        ```python
        from governmentreporter.utils.citations import format_cfr_citation

        # Basic CFR citation without year
        citation = format_cfr_citation("14", "91.817")
        print(citation)  # Output: "14 C.F.R. § 91.817"

        # CFR citation with year
        citation = format_cfr_citation("14", "91.817", "2025")
        print(citation)  # Output: "14 C.F.R. § 91.817 (2025)"

        # CFR citation with subsection
        citation = format_cfr_citation("42", "1983.1(a)(2)", "2024")
        print(citation)  # Output: "42 C.F.R. § 1983.1(a)(2) (2024)"
        ```
    """
    # Build the basic citation format
    citation = f"{title} C.F.R. § {section}"

    # Add year in parentheses if provided
    if year:
        citation = f"{citation} ({year})"

    return citation


def format_usc_citation(title: str, section: str, year: Optional[str] = None) -> str:
    """Format a United States Code (U.S.C.) citation in Bluebook style.

    This function creates properly formatted citations for federal statutes
    according to Bluebook rules. U.S.C. citations are essential for referencing
    federal laws in legal documents, court opinions, and academic writing.

    The United States Code is the official compilation of federal statutes
    enacted by Congress. It is organized into 54 titles covering various
    subject areas of federal law. Each title is further divided into chapters,
    sections, and subsections.

    U.S.C. Citation Components:
        - Title: The title number representing the subject area of law
        - Section: The specific statutory section number
        - Year: The year of the U.S.C. edition or supplement (optional)

    Common U.S.C. Titles:
        - Title 5: Government Organization and Employees
        - Title 12: Banks and Banking
        - Title 18: Crimes and Criminal Procedure
        - Title 26: Internal Revenue Code
        - Title 42: Public Health and Welfare

    Python Learning Notes:
        - Optional type hints indicate parameters that may be None
        - Conditional string formatting based on parameter presence
        - Clean separation of formatting logic for readability

    Args:
        title (str): The title number of the U.S.C. (e.g., "42" for public health).
        section (str): The section number (e.g., "1983" for civil rights claims).
            Can include subsections like "1983(a)(1)".
        year (Optional[str]): The year of the U.S.C. edition or supplement.
            If None, no year is included. Defaults to None.

    Returns:
        str: A properly formatted U.S.C. citation in Bluebook style.
            Format: "Title U.S.C. § Section (Year)" if year is provided,
            or "Title U.S.C. § Section" if year is not provided.

    Example Usage:
        ```python
        from governmentreporter.utils.citations import format_usc_citation

        # Basic U.S.C. citation without year
        citation = format_usc_citation("42", "1983")
        print(citation)  # Output: "42 U.S.C. § 1983"

        # U.S.C. citation with year
        citation = format_usc_citation("12", "5497", "2018")
        print(citation)  # Output: "12 U.S.C. § 5497 (2018)"

        # U.S.C. citation with subsection
        citation = format_usc_citation("18", "1001(a)(2)", "2024")
        print(citation)  # Output: "18 U.S.C. § 1001(a)(2) (2024)"
        ```
    """
    # Build the basic citation format
    citation = f"{title} U.S.C. § {section}"

    # Add year in parentheses if provided
    if year:
        citation = f"{citation} ({year})"

    return citation


def format_constitution_citation(
    article: Optional[str] = None,
    amendment: Optional[str] = None,
    section: Optional[str] = None,
    clause: Optional[str] = None,
) -> Optional[str]:
    """Format a United States Constitution citation in Bluebook style.

    This function creates properly formatted citations for constitutional
    provisions according to Bluebook rules. Constitutional citations are
    fundamental in legal writing, appearing in court opinions, legal briefs,
    and academic articles.

    The U.S. Constitution consists of:
        - Seven articles establishing the structure of government
        - Twenty-seven amendments adding rights and modifications
        - Various sections and clauses within each article/amendment

    Constitutional Citation Structure:
        - Articles: Cited as "U.S. Const. art. [Roman numeral]"
        - Amendments: Cited as "U.S. Const. amend. [Roman numeral]"
        - Sections: Added as ", § [number]"
        - Clauses: Added as ", cl. [number]"

    Important Constitutional Provisions:
        - Article I: Legislative Branch (Congress)
        - Article II: Executive Branch (President)
        - Article III: Judicial Branch (Courts)
        - First Amendment: Freedom of speech, religion, press
        - Fourth Amendment: Protection against unreasonable searches
        - Fifth Amendment: Due process, self-incrimination
        - Fourteenth Amendment: Equal protection, due process

    Python Learning Notes:
        - Multiple optional parameters with default None values
        - Validation logic ensures at least one required parameter
        - String building with conditional components
        - Early return pattern for invalid input

    Args:
        article (Optional[str]): The article number in Roman numerals
            (e.g., "I", "II", "III"). Cannot be combined with amendment.
        amendment (Optional[str]): The amendment number in Roman numerals
            (e.g., "XIV", "V", "I"). Cannot be combined with article.
        section (Optional[str]): The section number within the article or
            amendment (e.g., "2", "3"). Optional.
        clause (Optional[str]): The clause number within the section
            (e.g., "1", "2"). Optional.

    Returns:
        Optional[str]: A properly formatted constitutional citation in
            Bluebook style, or None if both article and amendment are
            provided or if neither is provided.

            Format examples:
            - "U.S. Const. art. I"
            - "U.S. Const. art. I, § 9, cl. 7"
            - "U.S. Const. amend. XIV"
            - "U.S. Const. amend. XIV, § 2"

    Example Usage:
        ```python
        from governmentreporter.utils.citations import format_constitution_citation

        # Article citation
        citation = format_constitution_citation(article="I", section="9", clause="7")
        print(citation)  # Output: "U.S. Const. art. I, § 9, cl. 7"

        # Amendment citation
        citation = format_constitution_citation(amendment="XIV", section="2")
        print(citation)  # Output: "U.S. Const. amend. XIV, § 2"

        # Simple article citation
        citation = format_constitution_citation(article="III")
        print(citation)  # Output: "U.S. Const. art. III"

        # Invalid: both article and amendment
        citation = format_constitution_citation(article="I", amendment="XIV")
        print(citation)  # Output: None
        ```
    """
    # Validate that exactly one of article or amendment is provided
    if (article and amendment) or (not article and not amendment):
        return None

    # Start building the citation
    if article:
        citation = f"U.S. Const. art. {article}"
    else:
        citation = f"U.S. Const. amend. {amendment}"

    # Add section if provided
    if section:
        citation = f"{citation}, § {section}"

    # Add clause if provided
    if clause:
        citation = f"{citation}, cl. {clause}"

    return citation


def parse_cfr_citations(text: str) -> list[Dict[str, str]]:
    """Extract and parse CFR citations from text.

    This function identifies Code of Federal Regulations citations within
    text using regular expressions. It handles various common formats used
    in legal documents, including those with and without spaces, different
    abbreviation styles, and subsection notations.

    The function recognizes multiple CFR citation patterns:
        - Standard format: "14 CFR 91.817"
        - With section symbol: "14 C.F.R. § 91.817"
        - With "Part": "14 CFR Part 36"
        - With subsections: "14 CFR 91.817(a)(1)"
        - Multiple sections: "14 CFR 91.817, 91.818, and 91.819"

    Regular Expression Explained:
        The regex pattern captures:
        - Title number (1-2 digits)
        - "CFR" or "C.F.R." with optional spaces
        - Optional "Part" or "§" symbol
        - Section numbers with optional subsections

    Python Learning Notes:
        - re.finditer() returns an iterator of match objects
        - Match groups extract specific parts of the pattern
        - List comprehension creates the result efficiently
        - Raw strings (r"...") prevent escape sequence issues

    Args:
        text (str): The text to search for CFR citations.

    Returns:
        list[Dict[str, str]]: A list of dictionaries, each containing:
            - "title": The CFR title number
            - "section": The section number (may include subsections)
            - "full_citation": The complete citation as found in text

    Example Usage:
        ```python
        from governmentreporter.utils.citations import parse_cfr_citations

        text = "The FAA shall repeal 14 CFR 91.817 and modify 14 C.F.R. § 91.818(a)."
        citations = parse_cfr_citations(text)
        for cite in citations:
            print(f"Found: {cite['full_citation']}")
            print(f"  Title: {cite['title']}, Section: {cite['section']}")

        # Output:
        # Found: 14 CFR 91.817
        #   Title: 14, Section: 91.817
        # Found: 14 C.F.R. § 91.818(a)
        #   Title: 14, Section: 91.818(a)
        ```
    """
    # Pattern to match CFR citations in various formats
    # Matches patterns like: 14 CFR 91.817, 14 C.F.R. § 91.817, 14 CFR Part 36
    pattern = r"(\d{1,2})\s*C\.?\s*F\.?\s*R\.?\s*(?:Part\s*|§\s*)?(\d+(?:\.\d+)?(?:\([a-z0-9]+\))*)"

    citations = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        citations.append(
            {
                "title": match.group(1),
                "section": match.group(2),
                "full_citation": match.group(0).strip(),
            }
        )

    return citations


def parse_usc_citations(text: str) -> list[Dict[str, str]]:
    """Extract and parse U.S.C. citations from text.

    This function identifies United States Code citations within text using
    regular expressions. It handles various formats commonly found in legal
    documents, court opinions, and regulatory materials.

    The function recognizes multiple U.S.C. citation patterns:
        - Standard format: "42 U.S.C. 1983"
        - With section symbol: "42 U.S.C. § 1983"
        - Alternative spacing: "42 USC 1983"
        - With subsections: "12 U.S.C. § 5497(a)(1)"
        - Multiple sections: "12 U.S.C. §§ 5497-5499"

    Regular Expression Components:
        - Title: Captured as 1-2 digit number
        - U.S.C.: Matched with optional periods and spaces
        - Section symbol: Optional § or §§ for multiple sections
        - Section number: With optional subsections in parentheses

    Python Learning Notes:
        - re.IGNORECASE flag makes pattern case-insensitive
        - match.group(0) returns the entire matched string
        - match.group(n) returns the nth captured group
        - Dictionaries provide structured return data

    Args:
        text (str): The text to search for U.S.C. citations.

    Returns:
        list[Dict[str, str]]: A list of dictionaries, each containing:
            - "title": The U.S.C. title number
            - "section": The section number (may include subsections)
            - "full_citation": The complete citation as found in text

    Example Usage:
        ```python
        from governmentreporter.utils.citations import parse_usc_citations

        text = "Under 42 U.S.C. § 1983, and pursuant to 12 U.S.C. 5497(a)(1)..."
        citations = parse_usc_citations(text)
        for cite in citations:
            print(f"Found: {cite['full_citation']}")
            print(f"  Title: {cite['title']}, Section: {cite['section']}")

        # Output:
        # Found: 42 U.S.C. § 1983
        #   Title: 42, Section: 1983
        # Found: 12 U.S.C. 5497(a)(1)
        #   Title: 12, Section: 5497(a)(1)
        ```
    """
    # Pattern to match U.S.C. citations in various formats
    # Matches: 42 U.S.C. 1983, 42 USC § 1983, 12 U.S.C. § 5497(a)(1)
    pattern = (
        r"(\d{1,2})\s*U\.?\s*S\.?\s*C\.?\s*(?:§§?\s*)?(\d+(?:\.\d+)?(?:\([a-z0-9]+\))*)"
    )

    citations = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        citations.append(
            {
                "title": match.group(1),
                "section": match.group(2),
                "full_citation": match.group(0).strip(),
            }
        )

    return citations


def parse_constitution_citations(text: str) -> list[Dict[str, Optional[str]]]:
    """Extract and parse U.S. Constitution citations from text.

    This function identifies constitutional citations within text using
    regular expressions. It handles various formats for both articles and
    amendments, including those with sections and clauses.

    The function recognizes multiple constitutional citation patterns:
        - Articles: "Art. I", "Article I", "Art. I, § 9, cl. 7"
        - Amendments: "First Amendment", "14th Amendment", "amend. XIV"
        - With Constitution prefix: "U.S. Const. art. I"
        - Informal references: "the Fourth Amendment"

    Roman Numeral Conversion:
        The function converts between Roman numerals and ordinal words:
        - "First Amendment" → "I"
        - "Fourteenth Amendment" → "XIV"
        - Handles amendments 1-27

    Python Learning Notes:
        - Multiple regex patterns for different citation styles
        - Dictionary mapping for number conversions
        - Optional dictionary values using Optional type hint
        - Complex pattern matching with named groups would improve this

    Args:
        text (str): The text to search for constitutional citations.

    Returns:
        list[Dict[str, Optional[str]]]: A list of dictionaries, each containing:
            - "type": Either "article" or "amendment"
            - "number": The article/amendment number (Roman numerals)
            - "section": The section number if present (Arabic numerals)
            - "clause": The clause number if present (Arabic numerals)
            - "full_citation": The complete citation as found in text

    Example Usage:
        ```python
        from governmentreporter.utils.citations import parse_constitution_citations

        text = "Under Art. I, § 9, cl. 7 and the Fifth Amendment..."
        citations = parse_constitution_citations(text)
        for cite in citations:
            print(f"Found: {cite['full_citation']}")
            print(f"  Type: {cite['type']}, Number: {cite['number']}")
            if cite['section']:
                print(f"  Section: {cite['section']}, Clause: {cite['clause']}")

        # Output:
        # Found: Art. I, § 9, cl. 7
        #   Type: article, Number: I
        #   Section: 9, Clause: 7
        # Found: Fifth Amendment
        #   Type: amendment, Number: V
        ```
    """
    citations = []

    # Pattern for articles with optional section and clause
    article_pattern = r"(?:U\.?S\.?\s*Const\.?\s*)?[Aa]rt(?:icle)?\.?\s+([IVX]+)(?:,?\s*§\s*(\d+))?(?:,?\s*cl\.?\s*(\d+))?"

    for match in re.finditer(article_pattern, text):
        citations.append(
            {
                "type": "article",
                "number": match.group(1),
                "section": match.group(2) if match.group(2) else None,
                "clause": match.group(3) if match.group(3) else None,
                "full_citation": match.group(0).strip(),
            }
        )

    # Pattern for amendments (handles both Roman numerals and ordinal words)
    amendment_pattern = (
        r"(?:U\.?S\.?\s*Const\.?\s*)?[Aa]mend(?:ment)?\s+([IVX]+)(?:,?\s*§\s*(\d+))?"
    )

    for match in re.finditer(amendment_pattern, text):
        citations.append(
            {
                "type": "amendment",
                "number": match.group(1),
                "section": match.group(2) if match.group(2) else None,
                "clause": None,
                "full_citation": match.group(0).strip(),
            }
        )

    # Pattern for ordinal word amendments (First Amendment, Fourteenth Amendment, etc.)
    ordinal_map = {
        "first": "I",
        "second": "II",
        "third": "III",
        "fourth": "IV",
        "fifth": "V",
        "sixth": "VI",
        "seventh": "VII",
        "eighth": "VIII",
        "ninth": "IX",
        "tenth": "X",
        "eleventh": "XI",
        "twelfth": "XII",
        "thirteenth": "XIII",
        "fourteenth": "XIV",
        "fifteenth": "XV",
        "sixteenth": "XVI",
        "seventeenth": "XVII",
        "eighteenth": "XVIII",
        "nineteenth": "XIX",
        "twentieth": "XX",
        "twenty-first": "XXI",
        "twenty-second": "XXII",
        "twenty-third": "XXIII",
        "twenty-fourth": "XXIV",
        "twenty-fifth": "XXV",
        "twenty-sixth": "XXVI",
        "twenty-seventh": "XXVII",
    }

    ordinal_pattern = r"\b(" + "|".join(ordinal_map.keys()) + r")\s+[Aa]mendment\b"

    for match in re.finditer(ordinal_pattern, text, re.IGNORECASE):
        ordinal = match.group(1).lower()
        citations.append(
            {
                "type": "amendment",
                "number": ordinal_map[ordinal],
                "section": None,
                "clause": None,
                "full_citation": match.group(0).strip(),
            }
        )

    return citations
