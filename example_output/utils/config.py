"""
Example output for config.py methods with return values.

This file demonstrates the methods in config.py that return output
and can be run in the main guard pattern.
"""

import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.governmentreporter.utils.config import get_court_listener_token, get_openai_api_key


def main():
    """Run examples of config.py methods that return output."""
    results = {}
    
    # Test get_court_listener_token
    try:
        token = get_court_listener_token()
        results["get_court_listener_token"] = {
            "method": "get_court_listener_token()",
            "result": {
                "token_present": bool(token),
                "token_length": len(token) if token else 0,
                "token_preview": token[:8] + "..." if token and len(token) > 8 else token
            }
        }
    except ValueError as e:
        results["get_court_listener_token"] = {
            "method": "get_court_listener_token()",
            "error": str(e)
        }
    except Exception as e:
        results["get_court_listener_token"] = {
            "method": "get_court_listener_token()",
            "error": f"Unexpected error: {str(e)}"
        }
    
    # Test get_openai_api_key
    try:
        api_key = get_openai_api_key()
        results["get_openai_api_key"] = {
            "method": "get_openai_api_key()",
            "result": {
                "key_present": bool(api_key),
                "key_length": len(api_key) if api_key else 0,
                "key_preview": api_key[:8] + "..." if api_key and len(api_key) > 8 else api_key
            }
        }
    except ValueError as e:
        results["get_openai_api_key"] = {
            "method": "get_openai_api_key()",
            "error": str(e)
        }
    except Exception as e:
        results["get_openai_api_key"] = {
            "method": "get_openai_api_key()",
            "error": f"Unexpected error: {str(e)}"
        }
    
    # Also show what environment variables are checked
    env_info = {
        "COURT_LISTENER_API_TOKEN": {
            "present": bool(os.getenv("COURT_LISTENER_API_TOKEN")),
            "length": len(os.getenv("COURT_LISTENER_API_TOKEN", ""))
        },
        "OPENAI_API_KEY": {
            "present": bool(os.getenv("OPENAI_API_KEY")),
            "length": len(os.getenv("OPENAI_API_KEY", ""))
        }
    }
    
    results["environment_variables"] = {
        "method": "Environment variable check",
        "result": env_info
    }
    
    # Print results in pretty JSON format
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()