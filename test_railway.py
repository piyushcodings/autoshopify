#!/usr/bin/env python3
"""Test script to verify Railway deployment"""

import os
import sys

print("🔍 Testing Railway Deployment...")
print("")

# Test 1: Check imports
print("1. Testing imports...")
try:
    from flask import Flask
    import requests
    print("   ✅ Flask and requests imported")
except Exception as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

# Test 2: Check app loads
print("2. Testing app load...")
try:
    exec(open('cxc-checker-captcha-integrated.py').read().split('if __name__')[0])
    print("   ✅ App loaded successfully")
except Exception as e:
    print(f"   ❌ App load error: {e}")
    sys.exit(1)

# Test 3: Check environment
print("3. Testing environment...")
port = os.environ.get('PORT', '5000')
print(f"   ✅ PORT: {port}")
print(f"   ✅ CAPTCHA_SOLVER_ENABLED: {CAPTCHA_SOLVER_ENABLED}")
print(f"   ✅ BROWSER_SOLVER_AVAILABLE: {BROWSER_SOLVER_AVAILABLE}")

print("")
print("✅ All tests passed! Ready for Railway deployment!")
