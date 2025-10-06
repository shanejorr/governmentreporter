#!/bin/bash

# Prompt:
# I ran my CI system on GitHub actions and received the errors and test failures identified in `scratch/ci_failures.log`. These errors were retrieved with the bash script in `scratch/ci_logs.sh`. Can you review the error logs and correct. For tests, if it is a valid test please fix the code to pass the test. If the test is not a good test, please fix the test. You can make breaking changes to the code.

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
