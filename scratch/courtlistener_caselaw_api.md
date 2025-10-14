# CourtListener REST API v4.3 - Case Law APIs Complete Reference

## Overview

The CourtListener REST API v4.3 provides comprehensive programmatic access to millions of legal opinions from federal and state courts across the United States. Launched in 2013 as the first API for legal decisions, the Case Law API enables developers to build their own case law collections, perform complex legal research, and access detailed court metadata. The API is built on Django REST Framework and maintained by Free Law Project, a 501(c)(3) nonprofit organization.

**Current Coverage**: 3,353 jurisdictions with ongoing data collection since 2009.

## Authentication & Access

### Authentication Methods

CourtListener uses **token-based authentication** via HTTP headers. All production implementations must include authentication, although many endpoints are open by default to encourage experimentation.

**Authentication Header Format:**
```
Authorization: Token <your-token-here>
```

**Obtaining Tokens:**
1. Create account at CourtListener.com
2. Log in and navigate to user profile
3. Generate API token
4. Include token in all production API requests

**Important**: The most common mistake is forgetting to enable authentication before deploying code to production.

### Rate Limiting

- **Limit**: 5,000 queries per hour for authenticated users
- **Enforcement**: Token-based tracking
- **Multiple Accounts**: Forbidden per project/organization
- **Throttling Response**: HTTP 429 (Too Many Requests)

### Maintenance Windows

**Scheduled Maintenance:**
- **When**: Thursday nights, 21:00-23:59 PT
- **Impact**: Potential downtime, API unavailability
- **Planning**: Avoid scheduling cron jobs during this window

### Access Levels

- **Public Endpoints**: Most Case Law APIs available to all authenticated users
- **Restricted Endpoints**: Some endpoints require special permissions (contact Free Law Project)
- **Experimentation**: Many endpoints accessible without authentication for testing

## Data Model & Architecture

### Hierarchical Structure

The Case Law API uses a four-tier hierarchical data model:

```
Courts → Dockets → Opinion Clusters → Opinions
```

### Object Relationships

**1. Courts**
- **Purpose**: Court identification and metadata
- **Contains**: Names, abbreviations, founding dates, jurisdictions
- **Relationship**: One court has many dockets

**2. Dockets**
- **Purpose**: Case-level metadata
- **Contains**: Docket numbers, case names, filing dates, parties
- **Relationship**: Each docket belongs to one court; one docket has many clusters

**3. Opinion Clusters**
- **Purpose**: Group related opinions (majority, dissent, concurrence)
- **Contains**: Citation information, precedential status, judge panels
- **Relationship**: Each cluster belongs to one docket; one cluster has many opinions

**4. Opinions**
- **Purpose**: Actual decision text and opinion-specific metadata
- **Contains**: Full text in multiple formats, author information, opinion type
- **Relationship**: Each opinion belongs to one cluster

### Design Principles

**Metadata Storage**: Data stored at the lowest hierarchical level to avoid duplication. Example: docket numbers stored on dockets (not opinions) to prevent repetition across multiple opinions in the same case.

**Normalization**: Related objects linked via URLs and IDs. Use double-underscore notation to traverse relationships in filters.

**Flexibility**: Multiple text formats available for opinions to accommodate different source materials and use cases.

## Core API Endpoints

### 1. Dockets Endpoint

**Base URL:** `https://www.courtlistener.com/api/rest/v4/dockets/`

**Purpose:** Access top-level case metadata including docket numbers, case names, parties, and filing information.

#### HTTP Methods

- **GET**: Retrieve dockets (list or detail)
- **OPTIONS**: Discover field descriptions, filters, ordering options

#### Making Requests

**List All Dockets:**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/dockets/"
```

**Get Specific Docket:**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/dockets/4214664/"
```

**Discover Fields and Filters:**
```bash
curl -X OPTIONS \
  --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/dockets/"
```

#### Response Format

**Example Response:**
```json
{
  "resource_uri": "https://www.courtlistener.com/api/rest/v4/dockets/4214664/",
  "id": 4214664,
  "court": "https://www.courtlistener.com/api/rest/v4/courts/dcd/",
  "court_id": "dcd",
  "original_court_info": null,
  "idb_data": null,
  "clusters": [],
  "audio_files": [],
  "assigned_to": "https://www.courtlistener.com/api/rest/v4/people/1124/",
  "referred_to": null,
  "panel": [],
  "absolute_url": "/docket/4214664/national-veterans-legal-services-program-v-united-states/",
  "date_created": "2016-08-20T07:25:37.448945-07:00",
  "date_modified": "2024-05-20T03:59:23.387426-07:00",
  "source": 9,
  "appeal_from_str": "",
  "assigned_to_str": "Paul L. Friedman",
  "referred_to_str": "",
  "panel_str": "",
  "date_last_index": "2024-05-20T03:59:23.387429-07:00",
  "date_cert_granted": null,
  "date_cert_denied": null,
  "date_argued": null,
  "date_reargued": null,
  "date_reargument_denied": null,
  "date_filed": "2016-04-21",
  "date_terminated": null,
  "date_last_filing": "2024-05-15",
  "case_name_short": "",
  "case_name": "NATIONAL VETERANS LEGAL SERVICES PROGRAM v. United States",
  "case_name_full": "",
  "slug": "national-veterans-legal-services-program-v-united-states",
  "docket_number": "1:16-cv-00745",
  "docket_number_core": "1600745",
  "pacer_case_id": "178502",
  "cause": "28:1346 Tort Claim",
  "nature_of_suit": "Other Statutory Actions",
  "jury_demand": "None",
  "jurisdiction_type": "U.S. Government Defendant",
  "appellate_fee_status": "",
  "appellate_case_type_information": "",
  "mdl_status": "",
  "filepath_ia": "https://www.archive.org/download/gov.uscourts.dcd.178502/gov.uscourts.dcd.178502.docket.xml",
  "filepath_ia_json": "https://archive.org/download/gov.uscourts.dcd.178502/gov.uscourts.dcd.178502.docket.json",
  "blocked": false
}
```

#### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique docket identifier |
| `court` | URL | Link to court object |
| `court_id` | string | Court abbreviation (e.g., "scotus", "ca9") |
| `case_name` | string | Full case name |
| `case_name_short` | string | Abbreviated case name |
| `case_name_full` | string | Extended case name with additional parties |
| `docket_number` | string | Full docket number from court |
| `docket_number_core` | string | Normalized docket number core |
| `date_filed` | date | Date case was filed |
| `date_argued` | date | Date case was argued |
| `date_terminated` | date | Date case was terminated |
| `date_last_filing` | date | Date of most recent filing |
| `assigned_to` | URL | Link to assigned judge |
| `assigned_to_str` | string | Assigned judge name as string |
| `panel` | array | List of panel judges (URLs) |
| `panel_str` | string | Panel judges as comma-separated string |
| `cause` | string | Cause of action |
| `nature_of_suit` | string | Nature of suit classification |
| `jurisdiction_type` | string | Type of jurisdiction |
| `pacer_case_id` | string | PACER system case identifier |
| `clusters` | array | List of associated opinion clusters |
| `blocked` | boolean | Whether blocked from public search engines |
| `source` | integer | Data source identifier |

#### Filtering Options

The Dockets endpoint supports extensive filtering capabilities. Use the OPTIONS request to discover all available filters.

**Common Filter Types:**

**Number Range Filters:**
```bash
# Exact match
curl "https://www.courtlistener.com/api/rest/v4/dockets/?id=4214664"

# Greater than or equal
curl "https://www.courtlistener.com/api/rest/v4/dockets/?id__gte=4214664"

# Range
curl "https://www.courtlistener.com/api/rest/v4/dockets/?id__range=4214664,4214700"
```

**Date Filters (ISO-8601 format required):**
```bash
# Filed after date
curl "https://www.courtlistener.com/api/rest/v4/dockets/?date_filed__gte=2020-01-01"

# Filed in date range
curl "https://www.courtlistener.com/api/rest/v4/dockets/?date_filed__range=2020-01-01,2020-12-31"
```

**Related Object Filters (double-underscore notation):**
```bash
# Filter by court
curl "https://www.courtlistener.com/api/rest/v4/dockets/?court=scotus"

# Filter by court jurisdiction
curl "https://www.courtlistener.com/api/rest/v4/dockets/?court__jurisdiction=F"

# Filter by court name pattern
curl "https://www.courtlistener.com/api/rest/v4/dockets/?court__full_name__startswith=district"
```

**String Filters:**
```bash
# Case name contains
curl "https://www.courtlistener.com/api/rest/v4/dockets/?case_name__contains=Smith"

# Docket number exact match
curl "https://www.courtlistener.com/api/rest/v4/dockets/?docket_number=1:16-cv-00745"
```

**Exclusion Filters (prepend with !):**
```bash
# Exclude federal appellate courts
curl "https://www.courtlistener.com/api/rest/v4/dockets/?court__jurisdiction!=F"

# Exclude specific court
curl "https://www.courtlistener.com/api/rest/v4/dockets/?court!=scotus"
```

#### Ordering Options

Control result ordering with the `order_by` parameter.

**Single Field Ordering:**
```bash
# Ascending order
curl "https://www.courtlistener.com/api/rest/v4/dockets/?order_by=date_filed"

# Descending order (prepend -)
curl "https://www.courtlistener.com/api/rest/v4/dockets/?order_by=-date_filed"
```

**Multiple Field Ordering:**
```bash
# Order by multiple fields
curl "https://www.courtlistener.com/api/rest/v4/dockets/?order_by=-date_modified,date_filed"
```

**Important**: Fields with null values are sorted at the end regardless of ascending/descending order.

#### Pagination

**Standard Pagination:**
```bash
# Second page
curl "https://www.courtlistener.com/api/rest/v4/dockets/?page=2"
```

**Cursor-Based Pagination** (for ordering by `id`, `date_modified`, `date_created`):
- Use `next` and `previous` URLs from response
- More efficient for large datasets
- Cannot use `page` parameter with cursor pagination

**Pagination Response:**
```json
{
  "count": 15000000,
  "next": "https://www.courtlistener.com/api/rest/v4/dockets/?cursor=cD0yMDE2LTA4...",
  "previous": null,
  "results": [...]
}
```

#### Field Selection

Reduce response size and improve performance by requesting only needed fields.

```bash
# Select specific fields
curl "https://www.courtlistener.com/api/rest/v4/dockets/?fields=id,case_name,date_filed"

# Select nested fields
curl "https://www.courtlistener.com/api/rest/v4/dockets/?fields=id,court__name"

# Exclude fields (omit parameter)
curl "https://www.courtlistener.com/api/rest/v4/dockets/?omit=clusters,audio_files"
```

#### Important Notes

- **Nested Objects Not Included**: Dockets response does NOT include nested docket entries, parties, or attorneys (doesn't scale for large dockets)
- **Related Objects**: Use separate endpoints with filtering to access related objects
- **Performance**: Always use field selection when you don't need all fields

---

### 2. Opinion Clusters Endpoint

**Base URL:** `https://www.courtlistener.com/api/rest/v4/clusters/`

**Purpose:** Access opinion clusters that group related opinions (majority, concurrence, dissent) with shared metadata.

#### HTTP Methods

- **GET**: Retrieve clusters (list or detail)
- **OPTIONS**: Discover field descriptions and filters

#### Making Requests

**List Clusters:**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/clusters/"
```

**Get Specific Cluster:**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/clusters/123456/"
```

**Get Clusters for Specific Docket:**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/clusters/?docket=4214664"
```

**Discover Available Options:**
```bash
curl -X OPTIONS \
  --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/clusters/"
```

#### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique cluster identifier (used in CourtListener URLs) |
| `docket` | URL | Link to parent docket |
| `sub_opinions` | array | List of opinions in this cluster |
| `citations` | array | Parallel citations for this cluster |
| `case_name` | string | Case name (may differ from docket case name) |
| `case_name_short` | string | Abbreviated case name |
| `case_name_full` | string | Full case name with all parties |
| `date_filed` | date | Filing date |
| `date_argued` | date | Argument date |
| `judges` | mixed | Judge information (string or linked objects) |
| `panel` | array | Panel of judges (linked objects when normalized) |
| `non_participating_judges` | array | Judges who didn't participate |
| `precedential_status` | string | Publication status (Published, Unpublished, etc.) |
| `citation_count` | integer | Number of times cited by later cases |
| `source` | string | Data source |
| `filepath_pdf_harvard` | string | Path to Harvard Caselaw Access Project PDF |
| `scdb_id` | string | Supreme Court Database ID |
| `blocked` | boolean | Whether blocked from public search engines |
| `nature_of_suit` | string | Nature of suit classification |

#### Judge Fields Behavior

Opinion clusters contain multiple judge-related fields with intelligent normalization:

- **Normalized Judges**: When CourtListener can match a judge name to a database record, it links to the judge API
- **Unnormalized Judges**: If no match exists, judge names stored as strings for later normalization
- **Multiple Fields**: `judges`, `panel`, `non_participating_judges` serve different purposes

#### Case Name Behavior

Case names on clusters may differ from docket case names:

**Example Scenario:**
- **Original Filing**: "Petroleum Co. v. Regan"
- **Docket Updates**: "Petroleum Co. v. New Administrator" (when administrator changes)
- **Cluster Retains**: "Petroleum Co. v. Regan" (original case name)

This preserves historical accuracy in legal citations.

#### Citations

The `citations` field contains parallel citations - multiple citation references to the same opinion published in different reporters.

**Example:**
```json
{
  "citations": [
    "576 U.S. 644",
    "135 S. Ct. 2584",
    "192 L. Ed. 2d 609"
  ]
}
```

#### Filtering and Ordering

Clusters support the same filtering and ordering patterns as dockets:

```bash
# Filter by court through docket
curl "https://www.courtlistener.com/api/rest/v4/clusters/?docket__court=scotus"

# Filter by date filed
curl "https://www.courtlistener.com/api/rest/v4/clusters/?date_filed__gte=2020-01-01"

# Filter by precedential status
curl "https://www.courtlistener.com/api/rest/v4/clusters/?precedential_status=Published"

# Order by citation count
curl "https://www.courtlistener.com/api/rest/v4/clusters/?order_by=-citation_count"
```

---

### 3. Opinions Endpoint

**Base URL:** `https://www.courtlistener.com/api/rest/v4/opinions/`

**Purpose:** Access the actual text of legal opinions and opinion-specific metadata.

#### HTTP Methods

- **GET**: Retrieve opinions (list or detail)
- **OPTIONS**: Discover field descriptions and filters

#### Making Requests

**List Opinions:**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/opinions/"
```

**Get Specific Opinion:**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/opinions/2812209/"
```

**Get Opinions for Cluster:**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/opinions/?cluster=123456"
```

**Get Supreme Court Opinions (cross-relationship filtering):**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/opinions/?cluster__docket__court=scotus"
```

#### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique opinion identifier |
| `cluster` | URL | Link to parent cluster |
| `type` | string | Opinion type (see types below) |
| `author` | URL | Link to authoring judge |
| `author_str` | string | Author name as string |
| `per_curiam` | boolean | Whether per curiam opinion |
| `joined_by` | array | Judges who joined this opinion |
| `download_url` | string | Original source URL (often unreliable) |
| `local_path` | string | Path to locally stored binary file |
| `opinions_cited` | array | Other opinions cited by this opinion |
| `ordering_key` | integer | Order within cluster (Harvard/Columbia only) |
| `extracted_by_ocr` | boolean | Whether text extracted via OCR |

#### Opinion Types

Opinion types are numbered for sorting priority (highest to lowest):

- **Lead Opinion**: Main opinion
- **Concurrence**: Agrees with outcome, different reasoning
- **Concurrence in Part**: Partially concurs
- **Dissent**: Disagrees with outcome
- **Combined Opinion**: Unidentified type or multiple types
- **Unanimous**: All judges agree
- **Majority**: Opinion by majority
- **Plurality**: Largest group without majority
- **Concur in Judgment**: Agrees with result only
- **Remittitur**: Order reducing damages
- **Rehearing**: Opinion on rehearing
- **On the Merits**: Substantive decision
- **On Motion to Strike Cost Bill**: Procedural decision

#### Text Fields (Critical for Performance)

Opinions contain text in multiple formats depending on source. **Use field selection to request only the format you need.**

**Recommended Primary Field:**
- `html_with_citations`: Each citation identified and hyperlinked (used on CourtListener website)

**Source-Specific Fields:**
- `html_lawbox`: From Lawbox donation
- `xml_harvard`: From Harvard Caselaw Access Project (OCR, may have errors)
- `html_anon_2020`: From anonymous 2020 source
- `html_columbia`: From Columbia collaboration
- `html`: From court websites (Word Perfect/HTML) or Resource.org
- `plain_text`: Extracted from court website PDFs or Microsoft Word documents

**Example with Field Selection:**
```bash
# Get only ID and HTML with citations (much faster)
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/opinions/2812209/?fields=id,html_with_citations,type,author_str"
```

**Performance Warning**: Requesting all text fields significantly slows responses. Always use field selection.

#### Cross-Relationship Filtering

Use double-underscore notation to filter across relationships:

```bash
# Get opinions from specific court
curl "https://www.courtlistener.com/api/rest/v4/opinions/?cluster__docket__court=scotus"

# Get opinions where court name starts with "district"
curl "https://www.courtlistener.com/api/rest/v4/opinions/?cluster__docket__court__full_name__startswith=district"

# Get opinions authored by specific judge
curl "https://www.courtlistener.com/api/rest/v4/opinions/?author=1234"

# Get dissenting opinions from 2020
curl "https://www.courtlistener.com/api/rest/v4/opinions/?type=040dissent&cluster__date_filed__year=2020"
```

#### Performance Best Practices

**Inefficient Approach** (don't do this):
```bash
# Gets all opinions, very slow
curl "https://www.courtlistener.com/api/rest/v4/opinions/?cluster__docket__court=scotus"
```

**Efficient Approach** (do this instead):
```bash
# 1. Get dockets for court
curl "https://www.courtlistener.com/api/rest/v4/dockets/?court=scotus&fields=id"

# 2. Get clusters for those dockets
curl "https://www.courtlistener.com/api/rest/v4/clusters/?docket__id__in=123,456,789&fields=id"

# 3. Get opinions with only needed text fields
curl "https://www.courtlistener.com/api/rest/v4/opinions/?cluster__id__in=999,888&fields=id,html_with_citations,type"
```

---

### 4. Courts Endpoint

**Base URL:** `https://www.courtlistener.com/api/rest/v4/courts/`

**Purpose:** Access metadata about the 3,353 courts in the CourtListener database.

#### HTTP Methods

- **GET**: Retrieve courts (list or detail)
- **OPTIONS**: Discover field descriptions and filters

#### Making Requests

**List All Courts:**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/courts/"
```

**Get Specific Court:**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/courts/scotus/"
```

**Discover Available Fields:**
```bash
curl -X OPTIONS \
  --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/courts/"
```

#### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Court abbreviation identifier (e.g., "scotus", "ca9") |
| `full_name` | string | Complete court name |
| `short_name` | string | Abbreviated court name |
| `citation_string` | string | Standard citation format |
| `jurisdiction` | string | Jurisdiction code (F=Federal Appellate, FD=Federal District, etc.) |
| `position` | integer | Display order position |
| `start_date` | date | Court founding date |
| `end_date` | date | Court termination date (if applicable) |
| `in_use` | boolean | Whether court is currently active |
| `has_opinion_scraper` | boolean | Whether CourtListener actively scrapes this court |
| `has_oral_argument_scraper` | boolean | Whether oral arguments are scraped |
| `url` | string | Court website URL |

#### Court ID System

Court IDs generally match PACER subdomains with some exceptions:

- **Supreme Court**: `scotus`
- **Ninth Circuit**: `ca9`
- **D.C. District Court**: `dcd`
- **Southern District of New York**: `nysd`

#### Jurisdiction Codes

| Code | Description |
|------|-------------|
| `F` | Federal Appellate |
| `FD` | Federal District |
| `FB` | Federal Bankruptcy |
| `FS` | Federal Special |
| `S` | State Supreme |
| `SA` | State Appellate |
| `ST` | State Trial |
| `I` | International |

#### Filtering Examples

```bash
# Get federal appellate courts
curl "https://www.courtlistener.com/api/rest/v4/courts/?jurisdiction=F"

# Get courts with "District" in name
curl "https://www.courtlistener.com/api/rest/v4/courts/?full_name__contains=District"

# Get active courts only
curl "https://www.courtlistener.com/api/rest/v4/courts/?in_use=true"

# Get courts with opinion scrapers
curl "https://www.courtlistener.com/api/rest/v4/courts/?has_opinion_scraper=true"
```

#### Caching Recommendation

The Courts endpoint changes infrequently. **You can cache this data** for improved performance. Update your cache monthly or when notified of changes.

---

### 5. Citations / Opinions-Cited Endpoint

**Base URL:** `https://www.courtlistener.com/api/rest/v4/opinions-cited/`

**Purpose:** Access the citation graph showing relationships between opinions - which opinions cite which others.

#### HTTP Methods

- **GET**: Retrieve citation relationships
- **OPTIONS**: Discover field descriptions and filters

#### Making Requests

**Get Authorities Cited by Opinion (Backward Citations):**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/opinions-cited/?citing_opinion=2812209"
```

**Get Opinions that Cite This Opinion (Forward Citations):**
```bash
curl --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/opinions-cited/?cited_opinion=2812209"
```

**Discover Filter Options:**
```bash
curl -X OPTIONS \
  --header 'Authorization: Token <your-token-here>' \
  "https://www.courtlistener.com/api/rest/v4/opinions-cited/"
```

#### Response Structure

**Example Response:**
```json
{
  "count": 403,
  "next": "https://www.courtlistener.com/api/rest/v4/opinions-cited/?cited_opinion=2812209&page=2",
  "previous": null,
  "results": [
    {
      "resource_uri": "https://www.courtlistener.com/api/rest/v4/opinions-cited/213931728/",
      "id": 213931728,
      "citing_opinion": "https://www.courtlistener.com/api/rest/v4/opinions/10008139/",
      "cited_opinion": "https://www.courtlistener.com/api/rest/v4/opinions/2812209/",
      "depth": 4
    }
  ]
}
```

#### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique citation relationship identifier |
| `citing_opinion` | URL | Opinion that contains the citation |
| `cited_opinion` | URL | Opinion being cited |
| `depth` | integer | Number of times cited opinion is referenced |

#### Understanding Depth

The `depth` field indicates how many times the cited opinion is referenced within the citing opinion.

**Interpretation:**
- **depth: 1** = Cited once (minor authority)
- **depth: 4** = Cited four times (likely important authority)
- **depth: 10+** = Central to the citing opinion's reasoning

#### Filter Options

**Available Filters:**
```json
{
  "id": {
    "type": "NumberRangeFilter",
    "lookup_types": ["exact", "gte", "gt", "lte", "lt", "range"]
  },
  "citing_opinion": {
    "type": "RelatedFilter",
    "lookup_types": "See available filters for 'Opinions'"
  },
  "cited_opinion": {
    "type": "RelatedFilter",
    "lookup_types": "See available filters for 'Opinions'"
  }
}
```

#### Complex Filtering Examples

**Get all citations from Supreme Court opinions:**
```bash
curl "https://www.courtlistener.com/api/rest/v4/opinions-cited/?citing_opinion__cluster__docket__court=scotus"
```

**Get citations to opinions from 2020:**
```bash
curl "https://www.courtlistener.com/api/rest/v4/opinions-cited/?cited_opinion__cluster__date_filed__year=2020"
```

**Get highly-cited references (depth >= 5):**
```bash
curl "https://www.courtlistener.com/api/rest/v4/opinions-cited/?depth__gte=5"
```

---

## Advanced Features

### Filtering System

CourtListener uses Django-style field lookups with extensive filtering capabilities.

#### Lookup Types

**NumberRangeFilter Operators:**
- `exact`: Exact match
- `gte`: Greater than or equal
- `gt`: Greater than
- `lte`: Less than or equal
- `lt`: Less than
- `range`: Within range (comma-separated: `field__range=10,20`)

**DateRangeFilter Operators:**
- Same as NumberRangeFilter
- Requires ISO-8601 format: `YYYY-MM-DD`
- Example: `date_filed__gte=2020-01-01`

**String Lookup Operators:**
- `contains`: Case-insensitive containment
- `icontains`: Explicitly case-insensitive
- `startswith`: Starts with string
- `endswith`: Ends with string
- `exact`: Exact match
- `iexact`: Case-insensitive exact match

**RelatedFilter (Double-Underscore Notation):**

Traverse object relationships using `__` (double underscore):

```bash
# Opinion → Cluster → Docket → Court
curl "https://www.courtlistener.com/api/rest/v4/opinions/?cluster__docket__court=scotus"

# Opinion → Cluster → Docket → Court → Full Name
curl "https://www.courtlistener.com/api/rest/v4/opinions/?cluster__docket__court__full_name__startswith=United"
```

#### Exclusion Filters

Negate any filter by prepending `!` (exclamation mark):

```bash
# Exclude federal appellate courts
curl "https://www.courtlistener.com/api/rest/v4/dockets/?court__jurisdiction!=F"

# Exclude Supreme Court
curl "https://www.courtlistener.com/api/rest/v4/clusters/?docket__court!=scotus"
```

#### Complex Filter Examples

**Multiple Filters (AND logic):**
```bash
# Federal appellate + filed after 2020
curl "https://www.courtlistener.com/api/rest/v4/dockets/?court__jurisdiction=F&date_filed__gte=2020-01-01"
```

**List Filters (IN logic):**
```bash
# Multiple specific courts
curl "https://www.courtlistener.com/api/rest/v4/dockets/?court__id__in=scotus,ca9,ca2"

# Multiple docket IDs
curl "https://www.courtlistener.com/api/rest/v4/clusters/?docket__id__in=123,456,789"
```

---

## HTTP Methods & Error Handling

### HTTP Status Codes

**200 OK:**
- Successful GET request
- Valid data returned

**201 Created:**
- Successful POST request
- New resource created

**400 Bad Request:**
- Invalid parameters
- Malformed query syntax
- Missing required fields

**401 Unauthorized:**
- Missing authentication token
- Invalid token

**403 Forbidden:**
- Valid authentication but insufficient permissions

**404 Not Found:**
- Resource doesn't exist
- Invalid cursor in pagination

**429 Too Many Requests:**
- Rate limit exceeded (5,000 requests/hour)
- Throttling applied

**500 Internal Server Error:**
- Server error
- Database or Elasticsearch issues

### Error Response Format

**Standard Error Response:**
```json
{
  "detail": "Error message describing the issue"
}
```

**Common Error Messages:**

**Invalid Cursor:**
```json
{"detail": "Invalid cursor"}
```
Solution: Restart query without cursor

**Query Syntax Errors:**
```json
{"detail": "The query contains unbalanced parentheses"}
```
Solution: Check query syntax

**Authentication Errors:**
```json
{"detail": "Authentication credentials were not provided."}
```
Solution: Add Authorization header

**Rate Limiting:**
```json
{"detail": "Request was throttled. Expected available in 3600 seconds."}
```
Solution: Wait for cool-down period

---

## Search API

**Base URL:** `https://www.courtlistener.com/api/rest/v4/search/`

### Type Parameter

| Type | Description |
|------|-------------|
| `o` | Opinions (case law) - DEFAULT |
| `r` | RECAP (dockets with nested docs) |
| `rd` | RECAP documents (flat) |
| `d` | Dockets only |
| `oa` | Oral arguments |
| `p` | People/judges |

### Making Requests

```bash
curl -X GET \
  --header 'Authorization: Token <your-token-here>' \
  'https://www.courtlistener.com/api/rest/v4/search/?q=constitutional+rights&type=o'
```

### Response Format (camelCase)

```json
{
  "count": 2343,
  "next": "https://www.courtlistener.com/api/rest/v4/search/?cursor=...",
  "previous": null,
  "results": [
    {
      "absolute_url": "/opinion/6613686/foo-v-foo/",
      "caseName": "Foo v. Foo",
      "citation": ["101 Haw. 235"],
      "cluster_id": 6613686,
      "court": "Hawaii Intermediate Court of Appeals",
      "court_id": "hawapp",
      "dateFiled": "2003-01-10",
      "docket_id": 63544014,
      "docketNumber": "24158",
      "snippet": "First 500 chars or <mark>highlighted</mark> text...",
      "status": "Published",
      "citeCount": 5,
      "meta": {
        "score": {"bm25_score": 235.87125}
      }
    }
  ]
}
```

### Search Operators

**Field-Specific:**
```bash
?q=caseName:miranda
?q=judge:ginsburg
?q=citation:"410 U.S. 113"
?q=court:scotus
?q=filed:[2020-01-01 TO *]
```

**Boolean:**
```bash
?q=constitutional AND rights
?q=miranda OR warnings
?q=miranda NOT police
?q=(constitutional OR statutory) AND rights
```

**Proximity:**
```bash
?q="constitutional rights"~5
```

### Caching

All search results are cached for **10 minutes** server-side. Do NOT use for real-time monitoring - use Webhook/Alert APIs instead.

---

## Performance Optimization

### Best Practices

1. **Use Field Selection** - Request only needed fields
2. **Filter at Appropriate Level** - Query dockets first, then related objects
3. **Use Cursor Pagination** - For large datasets
4. **Cache Static Data** - Courts endpoint changes rarely
5. **Batch Requests** - Use `id__in` filters instead of sequential requests
6. **Specific Filters** - Narrow queries as much as possible

### Efficient Query Pattern

```bash
# Step 1: Get Supreme Court dockets (minimal fields)
curl "https://www.courtlistener.com/api/rest/v4/dockets/?court=scotus&fields=id"

# Step 2: Get clusters for those dockets
curl "https://www.courtlistener.com/api/rest/v4/clusters/?docket__id__in=123,456,789&fields=id,case_name"

# Step 3: Get opinions with only needed text format
curl "https://www.courtlistener.com/api/rest/v4/opinions/?cluster__id__in=999,888&fields=id,html_with_citations"
```

---

## Complete Example Workflow

**Accessing Supreme Court opinions on constitutional rights:**

```bash
# 1. Search for relevant cases
curl --header 'Authorization: Token <YOUR-TOKEN>' \
  "https://www.courtlistener.com/api/rest/v4/search/?q=constitutional+rights&court=scotus&type=o"

# 2. Get specific cluster details
curl --header 'Authorization: Token <YOUR-TOKEN>' \
  "https://www.courtlistener.com/api/rest/v4/clusters/2812209/"

# 3. Get opinion text with citations
curl --header 'Authorization: Token <YOUR-TOKEN>' \
  "https://www.courtlistener.com/api/rest/v4/opinions/?cluster=2812209&fields=id,html_with_citations,type,author_str"

# 4. Get citation graph (what this opinion cites)
curl --header 'Authorization: Token <YOUR-TOKEN>' \
  "https://www.courtlistener.com/api/rest/v4/opinions-cited/?citing_opinion=2812209"

# 5. Get forward citations (what cites this opinion)
curl --header 'Authorization: Token <YOUR-TOKEN>' \
  "https://www.courtlistener.com/api/rest/v4/opinions-cited/?cited_opinion=2812209"
```

---

## Additional Resources

### Official Documentation

- **REST API Overview**: https://www.courtlistener.com/help/api/rest/
- **Bulk Data**: https://www.courtlistener.com/help/api/bulk-data/
- **Coverage**: https://www.courtlistener.com/help/coverage/
- **Search Operators**: https://www.courtlistener.com/help/search-operators/

### GitHub

- **Repository**: https://github.com/freelawproject/courtlistener
- **Models**: /cl/search/models.py
- **API Code**: /cl/api/

### Support

- **Forum**: GitHub Discussions
- **Email**: mike@free.law
- **Contact**: https://www.courtlistener.com/contact/

### Related Tools

**Citation Lookup API** (`/api/rest/v3/citation-lookup/`):
- Validate citations
- Parse citation text
- Match to CourtListener records
- Limit: 250 citations per request

**Webhook API**:
- Push notifications for docket updates
- Search alert triggers
- Real-time monitoring

**Bulk Data**:
- Complete database dumps
- CSV format
- Monthly regeneration
- For large-scale analysis

---

## Summary

The CourtListener REST API v4.3 Case Law APIs provide comprehensive access to millions of legal opinions through five primary endpoints:

1. **Dockets** - Case metadata and filing information
2. **Opinion Clusters** - Grouped opinions with shared metadata
3. **Opinions** - Full opinion text in multiple formats
4. **Courts** - Court identification and metadata
5. **Opinions-Cited** - Citation graph relationships

Key features include powerful filtering with Django-style lookups, flexible ordering, field selection for performance optimization, cursor-based pagination for large datasets, and comprehensive search capabilities via Elasticsearch.

Authentication uses token-based headers with a 5,000 requests/hour rate limit. The API follows RESTful principles with standard HTTP methods and status codes, JSON/XML response formats, and extensive error messaging.

For optimal performance: use field selection on all requests, filter at appropriate hierarchy levels, batch related requests, and cache static data. Always use OPTIONS requests to discover endpoint capabilities before implementing.

This documentation compiled from official CourtListener sources, GitHub repository analysis, and web research as of October 2025.
