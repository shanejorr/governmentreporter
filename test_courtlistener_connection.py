#!/usr/bin/env python3
"""Test script to diagnose CourtListener API connectivity issues."""

import socket
import httpx
import requests
from urllib.parse import urlparse

def test_dns_resolution():
    """Test DNS resolution for www.courtlistener.com"""
    print("1. Testing DNS resolution...")
    try:
        ip = socket.gethostbyname("www.courtlistener.com")
        print(f"   ✅ DNS resolved: www.courtlistener.com -> {ip}")
        return True
    except socket.gaierror as e:
        print(f"   ❌ DNS resolution failed: {e}")
        return False

def test_httpx_connection():
    """Test connection using httpx (same library as the script)"""
    print("\n2. Testing httpx connection...")
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get("https://www.courtlistener.com/api/rest/v4/opinions/", 
                                  params={"count": "on"})
            print(f"   ✅ httpx connection successful: Status {response.status_code}")
            return True
    except Exception as e:
        print(f"   ❌ httpx connection failed: {e}")
        return False

def test_requests_connection():
    """Test connection using requests library"""
    print("\n3. Testing requests library connection...")
    try:
        response = requests.get("https://www.courtlistener.com/api/rest/v4/opinions/", 
                                params={"count": "on"}, timeout=10)
        print(f"   ✅ requests connection successful: Status {response.status_code}")
        return True
    except Exception as e:
        print(f"   ❌ requests connection failed: {e}")
        return False

def test_alternative_dns():
    """Test with alternative DNS servers"""
    print("\n4. Testing with Google's public DNS...")
    try:
        import subprocess
        result = subprocess.run(["nslookup", "www.courtlistener.com", "8.8.8.8"], 
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("   ✅ Resolution via Google DNS successful")
            print(f"   Output: {result.stdout[:200]}...")
            return True
        else:
            print(f"   ❌ Resolution via Google DNS failed")
            return False
    except Exception as e:
        print(f"   ⚠️  Could not test alternative DNS: {e}")
        return False

def test_ping():
    """Test basic network connectivity"""
    print("\n5. Testing basic network connectivity...")
    try:
        import subprocess
        result = subprocess.run(["ping", "-c", "1", "8.8.8.8"], 
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("   ✅ Basic internet connectivity OK")
            return True
        else:
            print("   ❌ No internet connectivity")
            return False
    except Exception as e:
        print(f"   ⚠️  Could not test ping: {e}")
        return False

def main():
    print("=" * 60)
    print("CourtListener API Connectivity Test")
    print("=" * 60)
    
    # Run all tests
    dns_ok = test_dns_resolution()
    ping_ok = test_ping()
    httpx_ok = test_httpx_connection()
    requests_ok = test_requests_connection()
    alt_dns_ok = test_alternative_dns()
    
    # Provide diagnosis
    print("\n" + "=" * 60)
    print("DIAGNOSIS:")
    print("=" * 60)
    
    if not ping_ok:
        print("❌ No internet connectivity detected. Check your network connection.")
    elif not dns_ok:
        print("❌ DNS resolution issue. Try:")
        print("   1. Flush DNS cache: sudo dscacheutil -flushcache")
        print("   2. Check /etc/hosts file for conflicting entries")
        print("   3. Try different DNS servers (System Preferences > Network > Advanced > DNS)")
        print("   4. Restart your network connection")
    elif not httpx_ok and not requests_ok:
        print("❌ HTTPS connection blocked. Check:")
        print("   1. Firewall settings")
        print("   2. VPN or proxy configuration")
        print("   3. Corporate network restrictions")
    else:
        print("✅ Connection tests passed. The issue may be temporary.")
        print("   Try running the script again in a few minutes.")
    
    print("\nAdditional troubleshooting commands to try:")
    print("  curl -I https://www.courtlistener.com")
    print("  dig www.courtlistener.com")
    print("  traceroute www.courtlistener.com")

if __name__ == "__main__":
    main()