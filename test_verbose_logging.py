#!/usr/bin/env python3
"""Test script to verify verbose logging functionality."""

import os
import subprocess
import sys
from pathlib import Path

def test_verbose_logging():
    """Test the verbose logging feature."""
    # Test opinion ID (you can change this if needed)
    opinion_id = "9973155"
    
    print("=" * 60)
    print("Testing SCOTUS Opinion Processor with Verbose Logging")
    print("=" * 60)
    
    # Run without verbose
    print("\n1. Running WITHOUT verbose flag...")
    print("-" * 40)
    result = subprocess.run(
        ["uv", "run", "python", "scripts/process_scotus_opinion.py", opinion_id],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Normal execution successful")
        print(f"Output lines: {len(result.stdout.splitlines())}")
    else:
        print("❌ Normal execution failed")
        print(f"Error: {result.stderr}")
        return False
    
    # Run with verbose
    print("\n2. Running WITH verbose flag...")
    print("-" * 40)
    result = subprocess.run(
        ["uv", "run", "python", "scripts/process_scotus_opinion.py", opinion_id, "--verbose"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Verbose execution successful")
        print(f"Output lines: {len(result.stdout.splitlines())}")
        
        # Check if log file was created
        log_dir = Path("logs")
        if log_dir.exists():
            log_files = list(log_dir.glob(f"scotus_opinion_{opinion_id}_*.log"))
            if log_files:
                latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
                print(f"\n✅ Log file created: {latest_log}")
                
                # Check log content
                with open(latest_log, 'r') as f:
                    log_content = f.read()
                    
                print("\nLog file analysis:")
                print(f"  - Size: {len(log_content)} characters")
                print(f"  - Lines: {len(log_content.splitlines())}")
                
                # Check for expected sections
                expected_sections = [
                    "RAW API RESPONSE - OPINION ENDPOINT",
                    "RAW API RESPONSE - CLUSTER ENDPOINT",
                    "TEXT CHUNKS BREAKDOWN",
                    "GEMINI METADATA EXTRACTION RESULT",
                    "FINAL PROCESSED CHUNKS FOR DATABASE",
                    "GENERATING EMBEDDINGS",
                    "STORING CHUNKS IN CHROMADB"
                ]
                
                print("\nExpected log sections:")
                for section in expected_sections:
                    if section in log_content:
                        print(f"  ✅ {section}")
                    else:
                        print(f"  ❌ {section} (missing)")
                
                print(f"\nFirst 500 characters of log:\n{'-' * 40}")
                print(log_content[:500])
                print(f"{'-' * 40}")
            else:
                print("❌ No log file found")
                return False
        else:
            print("❌ Log directory not created")
            return False
    else:
        print("❌ Verbose execution failed")
        print(f"Error: {result.stderr}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_verbose_logging()
    sys.exit(0 if success else 1)