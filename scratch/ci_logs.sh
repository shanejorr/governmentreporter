#!/bin/bash

# Get the latest CI workflow run logs (failed jobs only)

# Get the most recent CI workflow run ID
run_id=$(gh run list --workflow "CI" --limit 1 --json databaseId --jq '.[0].databaseId')

# Check if we got a run ID
if [ -z "$run_id" ]; then
    echo "Error: No CI workflow runs found"
    exit 1
fi

echo "Fetching failed logs for CI run: $run_id"
echo "----------------------------------------"

# Display the failed logs
gh run view "$run_id" --log-failed
