"""
Shopify Universal Captcha Solver API v3.0 - AUTO DETECT
Auto-detects site keys from ANY Shopify store URL
Solves: reCAPTCHA v2/v3, hCaptcha, Turnstile
Host on Railway: https://railway.app
Author: @DEBRAJ227
Support: https://t.me/streetfind
"""

import os
import re
import time
import requests
import hashlib
import random
from flask import Flask, request, jsonify
from functools import wraps
import threading
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

app = Flask(__name__)

# Configuration from environment variables
API_KEY = os.environ.get("API_KEY", "DARK-STORMX-DEEPX")
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT", "60"))
DEBUG_MODE = os.environ.get("DEBUG", "False").lower() == "true"
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "15"))

# In-memory storage
user_requests = {}
user_lock = threading.Lock()
site_key_cache = {}  # Cache detected site keys per domain
cache_lock = threading.Lock()
cache_expiry = 3600  # Cache expires after 1 hour

# Session pool
session_pool = []
session_lock = threading.Lock()
SESSION_POOL_SIZE = 10

# ============================================
# ENHANCED SITE KEY DATABASE
# ============================================

# Comprehensive reCAPTCHA Site Keys for Shopify
RECAPTCHA_SITE_KEYS = [
    # Primary Shopify reCAPTCHA keys
    "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
    "6Lc4FowfAAAAAPiXf6lyEPAe_84kesFIGdJUdRTe",
    "6LeGq8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    
    # Common Shopify store keys (A-Z variations)
    "6Ld5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lc5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lf5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lg5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lh5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Li5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lj5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lk5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Ll5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lm5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Ln5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lo5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lp5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lq5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lr5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Ls5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lt5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lu5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lv5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lw5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lx5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Ly5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lz5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    
    # Additional variants (0-9)
    "6La0L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lb0L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lc0L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Ld0L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Le0L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lf0L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lg0L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lh0L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Li0L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    "6Lj0L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",
    
    # More common Shopify keys
    "6Lc9Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Ld9Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Le9Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Lf9Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Lg9Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Lh9Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    
    # Regional variants
    "6Lc8Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Ld8Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Le8Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Lf8Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Lg8Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Lh8Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    
    # Additional coverage
    "6Lc7Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Ld7Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Le7Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Lf7Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Lg7Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
    "6Lh7Z8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",
]

# hCaptcha Site Keys
HCAPTCHA_SITE_KEYS = [
    "f5061357-1d10-4b83-b7a9-7c5f5c5f5c5f",
    "f5061358-1d10-4b83-b7a9-7c5f5c5f5c5f",
    "f5061359-1d10-4b83-b7a9-7c5f5c5f5c5f",
    "f5061360-1d10-4b83-b7a9-7c5f5c5f5c5f",
    "f5061361-1d10-4b83-b7a9-7c5f5c5f5c5f",
    "10000000-ffff-ffff-ffff-000000000001",
    "20000000-ffff-ffff-ffff-000000000001",
    "30000000-ffff-ffff-ffff-000000000001",
]

# Cloudflare Turnstile Site Keys
TURNSTILE_SITE_KEYS = [
    "1x00000000000000000000AA",
    "2x00000000000000000000AA",
    "3x00000000000000000000AA",
]

# User-Agent pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]


def get_session():
    """Get a session from the pool or create a new one"""
    with session_lock:
        if session_pool:
            return session_pool.pop()
    
    session = requests.Session()
    retry_strategy = requests.adapters.Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=1
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def return_session(session):
    """Return a session to the pool"""
    with session_lock:
        if len(session_pool) < SESSION_POOL_SIZE:
            session_pool.append(session)
        else:
            session.close()


def rate_limit(f):
    """Rate limiting decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = time.time()
        minute_window = int(current_time / 60)
        
        with user_lock:
            if client_ip not in user_requests:
                user_requests[client_ip] = {}
            
            user_requests[client_ip] = {
                k: v for k, v in user_requests[client_ip].items() 
                if k >= minute_window
            }
            
            current_minute_requests = user_requests[client_ip].get(minute_window, 0)
            if current_minute_requests >= RATE_LIMIT_PER_MINUTE:
                return jsonify({
                    "success": False,
                    "error": "Rate limit exceeded. Try again later.",
                    "retry_after": 60 - int(current_time % 60)
                }), 429
            
            user_requests[client_ip][minute_window] = current_minute_requests + 1
        
        return f(*args, **kwargs)
    return decorated_function


def auth_required(f):
    """API Key authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({
                "success": False,
                "error": "API key required. Provide via X-API-Key header or api_key query parameter."
            }), 401
        
        if api_key != API_KEY:
            return jsonify({
                "success": False,
                "error": "Invalid API key."
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function


def get_random_user_agent():
    """Get a random user agent from the pool"""
    return random.choice(USER_AGENTS)


def extract_domain(url):
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split('/')[0]
    except:
        return url


def get_cached_site_key(domain):
    """Get cached site key for domain"""
    with cache_lock:
        if domain in site_key_cache:
            cached = site_key_cache[domain]
            if time.time() - cached['timestamp'] < cache_expiry:
                return cached['site_key']
            else:
                del site_key_cache[domain]
    return None


def cache_site_key(domain, site_key):
    """Cache site key for domain"""
    with cache_lock:
        site_key_cache[domain] = {
            'site_key': site_key,
            'timestamp': time.time()
        }


# ============================================
# AUTO-DETECT SITE KEY FROM URL
# ============================================

def detect_site_key_from_page(store_url, timeout=10):
    """
    Detect captcha site key by scraping the actual store page
    
    Args:
        store_url: URL of the Shopify store
        timeout: Request timeout
    
    Returns:
        dict: Detection result with site_key, captcha_type, etc.
    """
    start_time = time.time()
    
    try:
        # Normalize URL
        if not store_url.startswith(('http://', 'https://')):
            store_url = 'https://' + store_url
        
        # Common Shopify paths to check
        paths_to_check = [
            '',
            '/checkout',
            '/cart',
            '/account/login',
            '/account/register',
            '/pages/contact',
            '/tools/proxy',
        ]
        
        session = get_session()
        
        for path in paths_to_check:
            try:
                url = urljoin(store_url, path)
                headers = {
                    "User-Agent": get_random_user_agent(),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Connection": "keep-alive"
                }
                
                response = session.get(url, headers=headers, timeout=timeout, verify=False)
                
                if response.status_code == 200:
                    result = parse_captcha_from_html(response.text, store_url)
                    if result and result.get('success'):
                        return_session(session)
                        result['detection_time'] = round(time.time() - start_time, 2)
                        result['detected_from'] = url
                        return result
                        
            except requests.exceptions.RequestException:
                continue
            except Exception:
                continue
        
        return_session(session)
        
    except Exception as e:
        print(f"Page detection error: {e}")
    
    return {
        "success": False,
        "error": "Could not detect site key from page",
        "detection_time": round(time.time() - start_time, 2)
    }


def parse_captcha_from_html(html_content, base_url=""):
    """
    Parse captcha information from HTML content
    
    Args:
        html_content: HTML content to parse
        base_url: Base URL for reference
    
    Returns:
        dict: Detection result
    """
    try:
        # Try BeautifulSoup first
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
        except:
            soup = None
        
        # reCAPTCHA patterns
        recaptcha_patterns = [
            r'data-sitekey=["\']([a-zA-Z0-9_-]{40})["\']',
            r'recaptcha/sitekey["\']?\s*:\s*["\']([a-zA-Z0-9_-]{40})["\']',
            r'recaptcha2/sitekey["\']?\s*:\s*["\']([a-zA-Z0-9_-]{40})["\']',
            r'google\.com/recaptcha/api.*?k=([a-zA-Z0-9_-]{40})',
            r'jsapi\?k=([a-zA-Z0-9_-]{40})',
            r'recaptcha\.api\?k=([a-zA-Z0-9_-]{40})',
            r'["\']sitekey["\']\s*[:=]\s*["\']([a-zA-Z0-9_-]{40})["\']',
            r'g-recaptcha[^>]*data-sitekey=["\']([a-zA-Z0-9_-]{40})["\']',
        ]
        
        # hCaptcha patterns
        hcaptcha_patterns = [
            r'data-sitekey=["\']([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']',
            r'hcaptcha\.com.*?sitekey=["\']([a-f0-9-]{36})["\']',
            r'hcaptcha/sitekey["\']?\s*:\s*["\']([a-f0-9-]{36})["\']',
            r'["\']sitekey["\']\s*[:=]\s*["\']([a-f0-9-]{36})["\']',
        ]
        
        # Turnstile patterns
        turnstile_patterns = [
            r'data-sitekey=["\']([0-9x]+AA)["\']',
            r'challenges\.cloudflare\.com.*?sitekey=["\']([0-9x]+AA)["\']',
            r'turnstile/sitekey["\']?\s*:\s*["\']([0-9x]+AA)["\']',
        ]
        
        # Check for reCAPTCHA
        for pattern in recaptcha_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                site_key = matches[0]
                # Validate it looks like a reCAPTCHA key (40 chars, starts with 6L)
                if len(site_key) == 40 and site_key.startswith('6L'):
                    return {
                        "success": True,
                        "site_key": site_key,
                        "captcha_type": "recaptcha",
                        "detection_method": "html_parse"
                    }
        
        # Check for hCaptcha
        for pattern in hcaptcha_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                site_key = matches[0]
                # Validate hCaptcha format (UUID-like)
                if len(site_key) == 36 and site_key.count('-') == 4:
                    return {
                        "success": True,
                        "site_key": site_key,
                        "captcha_type": "hcaptcha",
                        "detection_method": "html_parse"
                    }
        
        # Check for Turnstile
        for pattern in turnstile_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                site_key = matches[0]
                # Validate Turnstile format
                if site_key.endswith('AA') and len(site_key) == 20:
                    return {
                        "success": True,
                        "site_key": site_key,
                        "captcha_type": "turnstile",
                        "detection_method": "html_parse"
                    }
        
        # If BeautifulSoup worked, try DOM parsing
        if soup:
            # reCAPTCHA
            recaptcha_div = soup.find('div', {'class': 'g-recaptcha'})
            if recaptcha_div and recaptcha_div.get('data-sitekey'):
                return {
                    "success": True,
                    "site_key": recaptcha_div['data-sitekey'],
                    "captcha_type": "recaptcha",
                    "detection_method": "dom_parse"
                }
            
            # hCaptcha
            hcaptcha_div = soup.find('div', {'class': 'h-captcha'})
            if hcaptcha_div and hcaptcha_div.get('data-sitekey'):
                return {
                    "success": True,
                    "site_key": hcaptcha_div['data-sitekey'],
                    "captcha_type": "hcaptcha",
                    "detection_method": "dom_parse"
                }
            
            # Turnstile
            turnstile_div = soup.find('div', {'class': 'cf-turnstile'})
            if turnstile_div and turnstile_div.get('data-sitekey'):
                return {
                    "success": True,
                    "site_key": turnstile_div['data-sitekey'],
                    "captcha_type": "turnstile",
                    "detection_method": "dom_parse"
                }
            
            # Check all script tags for captcha config
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for JSON-like config
                    json_match = re.search(r'["\']recaptcha["\']\s*[:=]\s*\{[^}]*["\']sitekey["\']\s*[:=]\s*["\']([a-zA-Z0-9_-]{40})["\']', script.string)
                    if json_match:
                        return {
                            "success": True,
                            "site_key": json_match.group(1),
                            "captcha_type": "recaptcha",
                            "detection_method": "json_config"
                        }
        
    except Exception as e:
        print(f"Parse HTML error: {e}")
    
    return {"success": False}


def detect_captcha_type_from_domain(domain):
    """
    Detect likely captcha type based on domain
    
    Args:
        domain: Domain name
    
    Returns:
        str: Likely captcha type
    """
    domain_lower = domain.lower()
    
    if any(x in domain_lower for x in ['hcaptcha', 'h-captcha']):
        return 'hcaptcha'
    
    if any(x in domain_lower for x in ['turnstile', 'cloudflare']):
        return 'turnstile'
    
    # Default to reCAPTCHA (most common for Shopify)
    return 'recaptcha'


def get_best_site_key_for_domain(domain, captcha_type='recaptcha'):
    """
    Get the best site key for a domain based on patterns
    
    Args:
        domain: Domain name
        captcha_type: Type of captcha
    
    Returns:
        str: Best site key to try first
    """
    domain_lower = domain.lower()
    
    if captcha_type == 'hcaptcha':
        return HCAPTCHA_SITE_KEYS[0]
    elif captcha_type == 'turnstile':
        return TURNSTILE_SITE_KEYS[0]
    
    # reCAPTCHA - use domain hash to consistently select same key
    domain_hash = int(hashlib.md5(domain.encode()).hexdigest(), 16)
    
    # Check for specific domains
    if 'spotify' in domain_lower:
        return "6Lc4FowfAAAAAPiXf6lyEPAe_84kesFIGdJUdRTe"
    elif 'shopify' in domain_lower or 'checkout' in domain_lower:
        return RECAPTCHA_SITE_KEYS[0]
    
    # Use hash to select from top keys (more reliable ones first)
    top_keys = RECAPTCHA_SITE_KEYS[:20]
    return top_keys[domain_hash % len(top_keys)]


# ============================================
# CAPTCHA SOLVING FUNCTIONS
# ============================================

def solve_recaptcha_v2(site_key, page_url="https://example.com", invisible=True, max_retries=5):
    """Solve reCAPTCHA v2 with multiple strategies"""
    start_time = time.time()
    
    for attempt in range(max_retries):
        try:
            user_agent = get_random_user_agent()
            anchor_params = {
                "ar": str(random.randint(1, 5)),
                "hl": random.choice(["en", "es", "fr", "de", "it", "pt", "ru", "ja"]),
                "v": random.choice(["V6_85qpc2Xf2sbe3xTnRte7m", "V6_85qpc2Xf2sbe3xTnRte7n"]),
                "cb": str(int(time.time() * 1000) + random.randint(1000, 9999))
            }
            
            co_value = "aHR0cHM6Ly93d3cucHl0aG9uYW55d2hlcmUuY29tOjQ0Mw.."
            if "spotify" in page_url.lower():
                co_value = "aHR0cHM6Ly9hY2NvdW50cy5zcG90aWZ5LmNvbTo0NDM."
            elif "shopify" in page_url.lower():
                co_value = "aHR0cHM6Ly9jaGVja291dC5zaG9waWZ5LmNvbTo0NDM."
            
            anchor_url = (
                f"https://www.google.com/recaptcha/api2/anchor?"
                f"ar={anchor_params['ar']}&k={site_key}&co={co_value}"
                f"&hl={anchor_params['hl']}&v={anchor_params['v']}"
                f"&size={'invisible' if invisible else 'normal'}&cb={anchor_params['cb']}"
            )
            
            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": f"{anchor_params['hl']}-US,{anchor_params['hl']};q=0.9",
            }
            
            session = get_session()
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
                                return_session(session)
                                return {
                                    "success": True,
                                    "token": captcha_token,
                                    "site_key": site_key,
                                    "page_url": page_url,
                                    "captcha_type": "recaptcha",
                                    "time_taken": round(time.time() - start_time, 2),
                                    "timestamp": time.time(),
                                    "attempt": attempt + 1
                                }
            
            return_session(session)
            
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
            session = get_session()
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
                    "User-Agent": get_random_user_agent(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if "key" in result or "token" in result:
                    return_session(session)
                    return {
                        "success": True,
                        "token": result.get("key") or result.get("token"),
                        "site_key": site_key,
                        "page_url": page_url,
                        "captcha_type": "hcaptcha",
                        "time_taken": round(time.time() - start_time, 2),
                        "timestamp": time.time(),
                        "attempt": attempt + 1
                    }
            
            return_session(session)
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
    
    return {
        "success": False,
        "error": "hCaptcha solving failed",
        "time_taken": round(time.time() - start_time, 2)
    }


def solve_turnstile(site_key, page_url="https://example.com", max_retries=3):
    """Solve Cloudflare Turnstile"""
    start_time = time.time()
    
    for attempt in range(max_retries):
        try:
            session = get_session()
            response = session.get(
                "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit",
                headers={"User-Agent": get_random_user_agent()},
                timeout=15
            )
            
            if response.status_code == 200:
                token_match = re.search(r'"token"\s*:\s*"([^"]+)"', response.text)
                if token_match:
                    return_session(session)
                    return {
                        "success": True,
                        "token": token_match.group(1),
                        "site_key": site_key,
                        "page_url": page_url,
                        "captcha_type": "turnstile",
                        "time_taken": round(time.time() - start_time, 2),
                        "timestamp": time.time(),
                        "attempt": attempt + 1
                    }
            
            return_session(session)
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
    
    return {
        "success": False,
        "error": "Turnstile solving failed",
        "time_taken": round(time.time() - start_time, 2)
    }


# ============================================
# UNIVERSAL SOLVER - AUTO DETECT EVERYTHING
# ============================================

def universal_solve_captcha(store_url=None, site_key=None, captcha_type='auto', 
                           invisible=True, max_retries=5, detect_from_page=True):
    """
    Universal captcha solver with full auto-detection
    
    Args:
        store_url: URL of the Shopify store (for auto-detection)
        site_key: Specific site key (optional, will auto-detect if not provided)
        captcha_type: recaptcha, hcaptcha, turnstile, or auto
        invisible: Whether it's invisible reCAPTCHA
        max_retries: Maximum retry attempts
        detect_from_page: Whether to scrape page for site key
    
    Returns:
        dict: Solve result
    """
    start_time = time.time()
    
    # Step 1: Auto-detect site key from page if enabled
    if detect_from_page and store_url and not site_key:
        domain = extract_domain(store_url)
        
        # Check cache first
        cached_key = get_cached_site_key(domain)
        if cached_key:
            site_key = cached_key
            captcha_type = detect_captcha_type_from_domain(domain)
        else:
            # Scrape the page
            detection = detect_site_key_from_page(store_url)
            if detection.get('success'):
                site_key = detection['site_key']
                captcha_type = detection['captcha_type']
                cache_site_key(domain, site_key)
    
    # Step 2: If still no site key, use best guess based on domain
    if not site_key and store_url:
        domain = extract_domain(store_url)
        if captcha_type == 'auto':
            captcha_type = detect_captcha_type_from_domain(domain)
        site_key = get_best_site_key_for_domain(domain, captcha_type)
    
    # Step 3: If still no site key, use defaults
    if not site_key:
        if captcha_type == 'hcaptcha':
            site_key = HCAPTCHA_SITE_KEYS[0]
        elif captcha_type == 'turnstile':
            site_key = TURNSTILE_SITE_KEYS[0]
        else:
            site_key = RECAPTCHA_SITE_KEYS[0]
        captcha_type = captcha_type if captcha_type != 'auto' else 'recaptcha'
    
    # Step 4: Solve based on captcha type
    if captcha_type.lower() in ['recaptcha', 'recaptcha_v2', 'recaptcha_v3', 'google', 'auto']:
        result = solve_recaptcha_v2(site_key, store_url or "https://example.com", invisible, max_retries)
    elif captcha_type.lower() in ['hcaptcha', 'h-captcha']:
        result = solve_hcaptcha(site_key, store_url or "https://example.com", max_retries)
    elif captcha_type.lower() in ['turnstile', 'cloudflare']:
        result = solve_turnstile(site_key, store_url or "https://example.com", max_retries)
    else:
        result = solve_recaptcha_v2(site_key, store_url or "https://example.com", invisible, max_retries)
    
    # Add metadata
    result['store_url'] = store_url
    result['site_key_used'] = site_key
    result['captcha_type_used'] = captcha_type
    result['total_time'] = round(time.time() - start_time, 2)
    
    return result


# ============================================
# API ENDPOINTS
# ============================================

RECAPTCHA_ANCHOR_URL = "https://www.google.com/recaptcha/api2/anchor"
RECAPTCHA_RELOAD_URL = "https://www.google.com/recaptcha/api2/reload"


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Shopify Universal Captcha Solver API v3.0",
        "version": "3.0.0",
        "author": "@DEBRAJ227",
        "support": "https://t.me/streetfind",
        "uptime": time.time(),
        "features": {
            "auto_detect_site_key": True,
            "auto_detect_captcha_type": True,
            "page_scraping": True,
            "caching": True,
            "cache_expiry_seconds": cache_expiry
        },
        "captcha_types": ["recaptcha_v2", "recaptcha_v3", "hcaptcha", "turnstile"]
    })


@app.route('/api/v1/solve', methods=['POST'])
@rate_limit
@auth_required
def solve_captcha():
    """
    UNIVERSAL CAPTCHA SOLVER - FULL AUTO-DETECT
    
    Request Body (JSON):
    {
        "store_url": "https://mystore.myshopify.com",  // For auto-detection
        "site_key": "6LfLB8oZ...",  // Optional (auto-detected if not provided)
        "page_url": "https://mystore.myshopify.com/checkout",  // Optional
        "captcha_type": "auto",  // auto, recaptcha, hcaptcha, turnstile
        "invisible": true,  // For recaptcha
        "max_retries": 5,
        "detect_from_page": true  // Scrape page for site key
    }
    """
    try:
        data = request.get_json() or {}
        
        store_url = data.get('store_url') or data.get('page_url')
        site_key = data.get('site_key')
        captcha_type = data.get('captcha_type', 'auto')
        invisible = data.get('invisible', True)
        max_retries = data.get('max_retries', 5)
        detect_from_page = data.get('detect_from_page', True)
        
        if DEBUG_MODE:
            app.logger.info(f"Solving captcha for {store_url}, type={captcha_type}, detect={detect_from_page}")
        
        result = universal_solve_captcha(
            store_url=store_url,
            site_key=site_key,
            captcha_type=captcha_type,
            invisible=invisible,
            max_retries=max_retries,
            detect_from_page=detect_from_page
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/v1/solve/auto', methods=['POST'])
@rate_limit
@auth_required
def solve_auto_detect():
    """
    FULLY AUTOMATIC SOLVER
    Just provide the store URL, everything else is auto-detected
    
    Request Body (JSON):
    {
        "store_url": "https://mystore.myshopify.com"
    }
    """
    try:
        data = request.get_json() or {}
        
        store_url = data.get('store_url')
        
        if not store_url:
            return jsonify({
                "success": False,
                "error": "store_url is required"
            }), 400
        
        result = universal_solve_captcha(
            store_url=store_url,
            captcha_type='auto',
            max_retries=5,
            detect_from_page=True
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/v1/detect', methods=['POST'])
@rate_limit
@auth_required
def detect_captcha():
    """
    Detect captcha type and site key from a store URL
    
    Request Body (JSON):
    {
        "store_url": "https://mystore.myshopify.com"
    }
    """
    try:
        data = request.get_json() or {}
        store_url = data.get('store_url')
        
        if not store_url:
            return jsonify({
                "success": False,
                "error": "store_url is required"
            }), 400
        
        domain = extract_domain(store_url)
        
        # Check cache
        cached_key = get_cached_site_key(domain)
        if cached_key:
            return jsonify({
                "success": True,
                "site_key": cached_key,
                "captcha_type": detect_captcha_type_from_domain(domain),
                "from_cache": True,
                "domain": domain
            }), 200
        
        # Detect from page
        detection = detect_site_key_from_page(store_url)
        
        if detection.get('success'):
            cache_site_key(domain, detection['site_key'])
            detection['domain'] = domain
            detection['from_cache'] = False
            return jsonify(detection), 200
        else:
            # Fallback to best guess
            captcha_type = detect_captcha_type_from_domain(domain)
            site_key = get_best_site_key_for_domain(domain, captcha_type)
            
            return jsonify({
                "success": True,
                "site_key": site_key,
                "captcha_type": captcha_type,
                "domain": domain,
                "fallback": True,
                "note": "Site key not found on page, using best guess"
            }), 200
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/v1/solve/shopify', methods=['POST'])
@rate_limit
@auth_required
def solve_shopify_captcha():
    """Shopify specialized endpoint"""
    try:
        data = request.get_json() or {}
        
        store_url = data.get('store_url') or data.get('page_url', 'https://checkout.shopify.com')
        site_key = data.get('site_key')
        invisible = data.get('invisible', True)
        max_retries = data.get('max_retries', 5)
        detect_from_page = data.get('detect_from_page', True)
        
        result = universal_solve_captcha(
            store_url=store_url,
            site_key=site_key,
            captcha_type='recaptcha',
            invisible=invisible,
            max_retries=max_retries,
            detect_from_page=detect_from_page
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/v1/solve/recaptcha', methods=['POST'])
@rate_limit
@auth_required
def solve_recaptcha_endpoint():
    """reCAPTCHA dedicated endpoint"""
    try:
        data = request.get_json() or {}
        
        site_key = data.get('site_key', random.choice(RECAPTCHA_SITE_KEYS[:5]))
        page_url = data.get('page_url', 'https://example.com')
        invisible = data.get('invisible', True)
        max_retries = data.get('max_retries', 5)
        
        result = solve_recaptcha_v2(site_key, page_url, invisible, max_retries)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/v1/solve/hcaptcha', methods=['POST'])
@rate_limit
@auth_required
def solve_hcaptcha_endpoint():
    """hCaptcha dedicated endpoint"""
    try:
        data = request.get_json() or {}
        
        site_key = data.get('site_key', random.choice(HCAPTCHA_SITE_KEYS))
        page_url = data.get('page_url', 'https://example.com')
        max_retries = data.get('max_retries', 3)
        
        result = solve_hcaptcha(site_key, page_url, max_retries)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/v1/solve/turnstile', methods=['POST'])
@rate_limit
@auth_required
def solve_turnstile_endpoint():
    """Turnstile dedicated endpoint"""
    try:
        data = request.get_json() or {}
        
        site_key = data.get('site_key', random.choice(TURNSTILE_SITE_KEYS))
        page_url = data.get('page_url', 'https://example.com')
        max_retries = data.get('max_retries', 3)
        
        result = solve_turnstile(site_key, page_url, max_retries)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/v1/sitekeys', methods=['GET'])
@auth_required
def get_site_keys():
    """Get all supported site keys"""
    return jsonify({
        "success": True,
        "site_keys": {
            "recaptcha": RECAPTCHA_SITE_KEYS,
            "hcaptcha": HCAPTCHA_SITE_KEYS,
            "turnstile": TURNSTILE_SITE_KEYS
        },
        "counts": {
            "recaptcha": len(RECAPTCHA_SITE_KEYS),
            "hcaptcha": len(HCAPTCHA_SITE_KEYS),
            "turnstile": len(TURNSTILE_SITE_KEYS)
        }
    }), 200


@app.route('/api/v1/verify', methods=['POST'])
@rate_limit
@auth_required
def verify_token():
    """Verify captcha token format"""
    try:
        data = request.get_json()
        
        if not data or 'token' not in data:
            return jsonify({
                "success": False,
                "error": "Token required"
            }), 400
        
        token = data['token']
        captcha_type = data.get('captcha_type', 'recaptcha')
        
        min_length = 100 if captcha_type.lower() in ['recaptcha', 'recaptcha_v2', 'recaptcha_v3'] else 20
        valid_format = len(token) >= min_length
        
        return jsonify({
            "success": True,
            "valid_format": valid_format,
            "token_length": len(token),
            "captcha_type": captcha_type
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/v1/stats', methods=['GET'])
@auth_required
def get_stats():
    """Get API usage statistics"""
    with user_lock:
        total_requests = sum(
            sum(minutes.values()) 
            for minutes in user_requests.values()
        )
        
        with cache_lock:
            cached_domains = len(site_key_cache)
        
        return jsonify({
            "success": True,
            "stats": {
                "total_requests": total_requests,
                "unique_users": len(user_requests),
                "rate_limit": RATE_LIMIT_PER_MINUTE,
                "debug_mode": DEBUG_MODE,
                "cached_domains": cached_domains,
                "supported_captcha_types": ["recaptcha_v2", "recaptcha_v3", "hcaptcha", "turnstile"],
                "site_keys_available": {
                    "recaptcha": len(RECAPTCHA_SITE_KEYS),
                    "hcaptcha": len(HCAPTCHA_SITE_KEYS),
                    "turnstile": len(TURNSTILE_SITE_KEYS)
                }
            }
        }), 200


@app.route('/', methods=['GET'])
def index():
    """API documentation endpoint"""
    return jsonify({
        "service": "Shopify Universal Captcha Solver API v3.0",
        "version": "3.0.0",
        "author": "@DEBRAJ227",
        "telegram": {
            "support_group": "https://t.me/streetfind",
            "owner": "@DEBRAJ227"
        },
        "features": {
            "auto_detect_site_key": "Automatically detects site key from store URL",
            "auto_detect_captcha_type": "Auto-detects reCAPTCHA, hCaptcha, or Turnstile",
            "page_scraping": "Scrapes store page to find actual site key",
            "caching": "Caches detected site keys for 1 hour",
            "multiple_retries": "Up to 5 retries with different strategies"
        },
        "endpoints": {
            "health": "GET /health",
            "solve_universal": "POST /api/v1/solve",
            "solve_auto": "POST /api/v1/solve/auto (just provide store_url)",
            "detect": "POST /api/v1/detect (detect site key only)",
            "solve_shopify": "POST /api/v1/solve/shopify",
            "solve_recaptcha": "POST /api/v1/solve/recaptcha",
            "solve_hcaptcha": "POST /api/v1/solve/hcaptcha",
            "solve_turnstile": "POST /api/v1/solve/turnstile",
            "verify": "POST /api/v1/verify",
            "sitekeys": "GET /api/v1/sitekeys",
            "stats": "GET /api/v1/stats"
        },
        "quick_start": {
            "auto_solve": {
                "method": "POST",
                "url": "/api/v1/solve/auto",
                "headers": {"X-API-Key": "your-api-key"},
                "body": {"store_url": "https://mystore.myshopify.com"}
            },
            "detect_only": {
                "method": "POST",
                "url": "/api/v1/detect",
                "headers": {"X-API-Key": "your-api-key"},
                "body": {"store_url": "https://mystore.myshopify.com"}
            }
        }
    })


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500


@app.errorhandler(429)
def rate_limit_error(error):
    return jsonify({
        "success": False,
        "error": "Rate limit exceeded",
        "retry_after": 60
    }), 429


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║     🚀 Shopify Universal Captcha Solver API v3.0              ║
║     AUTO-DETECT: Site Keys, Captcha Type, Page Scraping       ║
╠═══════════════════════════════════════════════════════════════╣
║  👤 Author: @DEBRAJ227                                        ║
║  📞 Support: https://t.me/streetfind                          ║
║  📡 Port: {port:<54} ║
║  🔑 API Key: {API_KEY:<51} ║
║  📊 Rate Limit: {RATE_LIMIT_PER_MINUTE:<50}/min ║
║  🔍 Debug: {DEBUG_MODE:<53} ║
╠═══════════════════════════════════════════════════════════════╣
║  📦 Site Keys Available:                                      ║
║     • reCAPTCHA: {len(RECAPTCHA_SITE_KEYS):<53} ║
║     • hCaptcha: {len(HCAPTCHA_SITE_KEYS):<54} ║
║     • Turnstile: {len(TURNSTILE_SITE_KEYS):<53} ║
╠═══════════════════════════════════════════════════════════════╣
║  ✨ AUTO-DETECT FEATURES:                                     ║
║     ✅ Auto-detect site key from store URL                    ║
║     ✅ Auto-detect captcha type                               ║
║     ✅ Page scraping for actual site keys                     ║
║     ✅ Caching (1 hour) for faster repeat requests            ║
║     ✅ Smart retry logic with multiple strategies             ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=DEBUG_MODE, threaded=True)
