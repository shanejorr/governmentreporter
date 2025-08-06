#!/usr/bin/env python3
"""Simple test to verify CourtListener API access with your token."""

import os
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_with_token():
    """Test the API with authentication token"""
    token = os.getenv("COURT_LISTENER_API_TOKEN")
    
    if not token:
        print("❌ No COURT_LISTENER_API_TOKEN found in environment")
        print("   Set it with: export COURT_LISTENER_API_TOKEN='your-token-here'")
        print("   Or add it to your .env file")
        return False
    
    print(f"✅ Found API token: {token[:10]}...")
    
    print("\nTesting API connection...")
    headers = {
        "Authorization": f"Token {token}",
        "User-Agent": "GovernmentReporter/0.1.0"
    }
    
    try:
        # Test with a simple count request
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                "https://www.courtlistener.com/api/rest/v4/opinions/",
                headers=headers,
                params={
                    "cluster__docket__court": "scotus",
                    "date_created__gte": "2025-01-01",
                    "count": "on"
                }
            )
            response.raise_for_status()
            data = response.json()
            count = data.get("count", 0)
            print(f"✅ API connection successful!")
            print(f"   Found {count} SCOTUS opinions since 2025-01-01")
            return True
            
    except httpx.ConnectError as e:
        print(f"❌ Connection error: {e}")
        print("   This is likely a network/DNS issue")
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP error {e.response.status_code}: {e.response.text[:200]}")
        if e.response.status_code == 401:
            print("   Your API token may be invalid")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    return False

if __name__ == "__main__":
    test_api_with_token()