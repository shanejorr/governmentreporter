#!/bin/bash

# Script to fetch Supreme Court opinion text from CourtListener API
# Usage: ./pull_opinion_text.sh <opinion_id>

set -euo pipefail

# Check if opinion_id argument is provided
if [ $# -eq 0 ]; then
    echo "Error: No opinion ID provided"
    echo "Usage: $0 <opinion_id>"
    echo "Example: $0 108713"
    exit 1
fi

OPINION_ID="$1"

# Load COURT_LISTENER_API_TOKEN from .env file if it exists
if [ -f .env ]; then
    COURT_LISTENER_API_TOKEN=$(grep -v '^#' .env | grep COURT_LISTENER_API_TOKEN | cut -d '=' -f 2)
fi

# Check if API token is set
if [ -z "${COURT_LISTENER_API_TOKEN:-}" ]; then
    echo "Error: COURT_LISTENER_API_TOKEN not found in environment or .env file"
    echo "Please set your CourtListener API token in .env"
    exit 1
fi

# Fetch opinion from CourtListener API
API_URL="https://www.courtlistener.com/api/rest/v4/opinions/${OPINION_ID}/"

echo "Fetching opinion ${OPINION_ID} from CourtListener API..."
echo "URL: ${API_URL}"
echo ""

# Fetch and format JSON output
curl -s -H "Authorization: Token ${COURT_LISTENER_API_TOKEN}" "${API_URL}" | jq '.'
