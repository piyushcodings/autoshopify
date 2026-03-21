# 🚀 Auto-Detect Captcha Solver - Usage Guide

**Just provide the store URL - everything else is automatic!**

Support: [StreetFind](https://t.me/streetfind) | Author: [@DEBRAJ227](https://t.me/deebuchecked)

---

## ✨ What is Auto-Detect?

The API now **automatically**:

1. ✅ **Scrapes the store page** to find the actual site key
2. ✅ **Detects captcha type** (reCAPTCHA, hCaptcha, Turnstile)
3. ✅ **Caches detected keys** for 1 hour (faster repeat requests)
4. ✅ **Selects best site key** based on domain patterns
5. ✅ **Retries with multiple strategies** for maximum success

**You just provide the store URL - that's it!**

---

## 🎯 Quick Start - Auto Solve

### Method 1: Fully Automatic (Recommended)

```python
import requests

API_URL = "https://your-app.railway.app"
API_KEY = "DARK-STORMX-DEEPX"

def solve_captcha_auto(store_url):
    """
    Fully automatic captcha solver
    Just provide the store URL!
    """
    response = requests.post(
        f"{API_URL}/api/v1/solve/auto",
        headers={"X-API-Key": API_KEY},
        json={"store_url": store_url},
        timeout=30
    )
    
    result = response.json()
    
    if result.get("success"):
        return result["token"]
    else:
        raise Exception(result.get("error"))

# Usage - ANY Shopify store!
token = solve_captcha_auto("https://mystore.myshopify.com")
print(f"✅ Token: {token[:50]}...")
```

### Method 2: Universal Endpoint with Auto-Detect

```python
def solve_captcha_universal(store_url):
    """
    Universal solver with auto-detect enabled
    """
    response = requests.post(
        f"{API_URL}/api/v1/solve",
        headers={"X-API-Key": API_KEY},
        json={
            "store_url": store_url,
            "captcha_type": "auto",  # Auto-detect type
            "detect_from_page": True,  # Scrape page for site key
            "max_retries": 5
        },
        timeout=30
    )
    
    result = response.json()
    
    if result.get("success"):
        print(f"✅ Solved in {result.get('time_taken', 'N/A')}s")
        print(f"📍 Detected from: {result.get('detected_from', 'N/A')}")
        print(f"🔑 Site key: {result.get('site_key_used', 'N/A')}")
        print(f"📌 Captcha type: {result.get('captcha_type_used', 'N/A')}")
        return result["token"]
    
    return None

# Usage
token = solve_captcha_universal("https://example-store.com")
```

---

## 🔍 Detect Only (Without Solving)

Want to just detect the site key and captcha type without solving?

```python
def detect_captcha_info(store_url):
    """
    Detect captcha info from store URL
    Returns site key, captcha type, etc.
    """
    response = requests.post(
        f"{API_URL}/api/v1/detect",
        headers={"X-API-Key": API_KEY},
        json={"store_url": store_url},
        timeout=15
    )
    
    result = response.json()
    
    if result.get("success"):
        print(f"🔑 Site Key: {result.get('site_key')}")
        print(f"📌 Captcha Type: {result.get('captcha_type')}")
        print(f"🌐 Domain: {result.get('domain')}")
        print(f"💾 From Cache: {result.get('from_cache', False)}")
        
        if result.get('fallback'):
            print(f"⚠️ Note: {result.get('note', 'Using best guess')}")
        
        return {
            "site_key": result["site_key"],
            "captcha_type": result["captcha_type"]
        }
    
    return None

# Usage
info = detect_captcha_info("https://mystore.myshopify.com")
```

---

## 🛍️ Real-World Examples

### Example 1: Solve for Any Shopify Store

```python
stores = [
    "https://gymshark.com",
    "https://allbirds.com",
    "https://fashionnova.com",
    "https://colourpop.com",
    "https://kylie-cosmetics.com",
]

for store in stores:
    try:
        token = solve_captcha_auto(store)
        print(f"✅ {store}: Success!")
    except Exception as e:
        print(f"❌ {store}: {str(e)}")
```

### Example 2: Solve with Custom Options

```python
response = requests.post(
    f"{API_URL}/api/v1/solve",
    headers={"X-API-Key": API_KEY},
    json={
        "store_url": "https://mystore.myshopify.com",
        "captcha_type": "recaptcha",  # Force specific type
        "invisible": True,
        "max_retries": 5,
        "detect_from_page": True  # Scrape for actual site key
    },
    timeout=30
)

result = response.json()
```

### Example 3: Detect Then Solve

```python
# First, detect the captcha info
detect_response = requests.post(
    f"{API_URL}/api/v1/detect",
    headers={"X-API-Key": API_KEY},
    json={"store_url": "https://mystore.myshopify.com"},
    timeout=15
)

detect_result = detect_response.json()

if detect_result.get("success"):
    site_key = detect_result["site_key"]
    captcha_type = detect_result["captcha_type"]
    
    print(f"✅ Detected: {captcha_type} with key {site_key[:20]}...")
    
    # Now solve with detected info
    solve_response = requests.post(
        f"{API_URL}/api/v1/solve",
        headers={"X-API-Key": API_KEY},
        json={
            "store_url": "https://mystore.myshopify.com",
            "site_key": site_key,  # Use detected key
            "captcha_type": captcha_type,
            "max_retries": 5
        },
        timeout=30
    )
    
    solve_result = solve_response.json()
    
    if solve_result.get("success"):
        print(f"✅ Solved! Token: {solve_result['token'][:50]}...")
```

---

## 🔧 Integration with Your CC Bot

### Updated Bot Integration

```python
# Add to your bot
CAPTCHA_API_URL = "https://your-app.railway.app"
CAPTCHA_API_KEY = "DARK-STORMX-DEEPX"

def get_captcha_token_auto(store_url, max_retries=5):
    """
    Auto-detect captcha from ANY Shopify store
    """
    try:
        response = requests.post(
            f"{CAPTCHA_API_URL}/api/v1/solve/auto",
            headers={"X-API-Key": CAPTCHA_API_KEY},
            json={"store_url": store_url},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                time_taken = data.get('time_taken', 'N/A')
                captcha_type = data.get('captcha_type_used', 'recaptcha')
                detected_from = data.get('detected_from', 'N/A')
                
                print(f"✅ Captcha solved via API in {time_taken}s")
                print(f"   Type: {captcha_type}")
                print(f"   Detected from: {detected_from}")
                
                return data["token"]
            else:
                print(f"❌ API error: {data.get('error', 'Unknown')}")
        else:
            print(f"❌ API request failed: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("❌ API timeout")
    except Exception as e:
        print(f"❌ API error: {e}")
    
    return None

# Use in your check_site function
def check_site(site, cc, proxy=None):
    """Check site with auto-detect captcha solving"""
    
    # Extract store URL from site (adjust based on your needs)
    store_url = extract_store_url_from_site(site)
    
    # Get captcha token with auto-detect
    captcha_token = get_captcha_token_auto(store_url)
    
    if captcha_token:
        # Use token in your request
        # ... your existing code ...
        pass
    
    # ... rest of your code ...

def extract_store_url_from_site(site):
    """Extract store URL from your site format"""
    # Implement based on your site format
    # Example: if site is "example.com", return "https://example.com"
    if not site.startswith(('http://', 'https://')):
        return 'https://' + site
    return site
```

---

## 📊 How Auto-Detect Works

### Step-by-Step Process

```
1. User provides store_url
   ↓
2. Check cache for this domain
   ↓ (if cached)
3. Use cached site key → Solve captcha
   ↓ (if not cached)
4. Scrape store page (multiple paths)
   ↓
5. Parse HTML for captcha info
   - reCAPTCHA: data-sitekey, g-recaptcha
   - hCaptcha: h-captcha, data-sitekey
   - Turnstile: cf-turnstile, data-sitekey
   ↓
6. Extract site key and type
   ↓
7. Cache for 1 hour
   ↓
8. Solve captcha
   ↓
9. Return token with metadata
```

### Detection Methods

1. **HTML Pattern Matching** - Regex patterns for common captcha implementations
2. **DOM Parsing** - BeautifulSoup to find captcha elements
3. **Script Analysis** - Parse JavaScript for captcha config
4. **Domain Heuristics** - Smart guesses based on domain patterns

---

## 🎛️ API Parameters

### POST /api/v1/solve/auto

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `store_url` | string | ✅ Yes | - | URL of the Shopify store |

**Example:**
```json
{
  "store_url": "https://mystore.myshopify.com"
}
```

### POST /api/v1/solve

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `store_url` | string | ⚠️ Recommended | - | Store URL for auto-detect |
| `site_key` | string | ❌ No | auto | Specific site key (auto-detected if not provided) |
| `captcha_type` | string | ❌ No | auto | recaptcha, hcaptcha, turnstile, or auto |
| `invisible` | boolean | ❌ No | true | For reCAPTCHA invisible |
| `max_retries` | integer | ❌ No | 5 | Maximum retry attempts |
| `detect_from_page` | boolean | ❌ No | true | Scrape page for site key |

**Example:**
```json
{
  "store_url": "https://mystore.myshopify.com",
  "captcha_type": "auto",
  "invisible": true,
  "max_retries": 5,
  "detect_from_page": true
}
```

### POST /api/v1/detect

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `store_url` | string | ✅ Yes | - | URL to detect captcha from |

**Example:**
```json
{
  "store_url": "https://mystore.myshopify.com"
}
```

---

## 📈 Response Format

### Success Response

```json
{
  "success": true,
  "token": "03AGdBq...long_token_here",
  "site_key": "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
  "page_url": "https://mystore.myshopify.com",
  "captcha_type": "recaptcha",
  "time_taken": 2.34,
  "timestamp": 1710934800.123,
  "attempt": 1,
  "store_url": "https://mystore.myshopify.com",
  "site_key_used": "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
  "captcha_type_used": "recaptcha",
  "total_time": 3.45,
  "detected_from": "https://mystore.myshopify.com/checkout",
  "detection_method": "html_parse"
}
```

### Detect Response

```json
{
  "success": true,
  "site_key": "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
  "captcha_type": "recaptcha",
  "domain": "mystore.myshopify.com",
  "from_cache": false,
  "detection_time": 1.23,
  "detected_from": "https://mystore.myshopify.com/checkout",
  "detection_method": "html_parse"
}
```

### Error Response

```json
{
  "success": false,
  "error": "Could not detect site key from page",
  "time_taken": 2.34
}
```

---

## 🧪 Testing

### Test Auto-Detect on Multiple Stores

```python
import requests

API_URL = "https://your-app.railway.app"
API_KEY = "DARK-STORMX-DEEPX"

test_stores = [
    "https://gymshark.com",
    "https://allbirds.com",
    "https://fashionnova.com",
]

for store in test_stores:
    print(f"\n🔍 Testing: {store}")
    
    # Detect only
    detect_response = requests.post(
        f"{API_URL}/api/v1/detect",
        headers={"X-API-Key": API_KEY},
        json={"store_url": store},
        timeout=15
    )
    
    detect_result = detect_response.json()
    
    if detect_result.get("success"):
        print(f"   ✅ Site Key: {detect_result['site_key']}")
        print(f"   📌 Type: {detect_result['captcha_type']}")
        print(f"   💾 Cached: {detect_result.get('from_cache', False)}")
        
        # Now solve
        solve_response = requests.post(
            f"{API_URL}/api/v1/solve/auto",
            headers={"X-API-Key": API_KEY},
            json={"store_url": store},
            timeout=30
        )
        
        solve_result = solve_response.json()
        
        if solve_result.get("success"):
            print(f"   ✅ Solved! Token: {solve_result['token'][:50]}...")
            print(f"   ⏱️ Time: {solve_result.get('time_taken', 'N/A')}s")
        else:
            print(f"   ❌ Solve failed: {solve_result.get('error', 'Unknown')}")
    else:
        print(f"   ❌ Detect failed: {detect_result.get('error', 'Unknown')}")
```

---

## 🆘 Troubleshooting

### "Could not detect site key from page"

**Solution 1:** Enable fallback (automatic)
```python
# The API automatically falls back to best-guess site keys
# No action needed - it will try multiple keys
```

**Solution 2:** Manually specify site key
```python
response = requests.post(
    f"{API_URL}/api/v1/solve",
    headers={"X-API-Key": API_KEY},
    json={
        "store_url": "https://mystore.myshopify.com",
        "site_key": "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
        "detect_from_page": False  # Skip detection
    }
)
```

### Detection is Slow

**Cause:** Page scraping takes time (2-5 seconds)

**Solution:** Use caching (automatic)
```python
# Second request to same domain will be faster (cached for 1 hour)
# No action needed - caching is automatic
```

### Wrong Captcha Type Detected

**Solution:** Force specific type
```python
response = requests.post(
    f"{API_URL}/api/v1/solve",
    headers={"X-API-Key": API_KEY},
    json={
        "store_url": "https://mystore.myshopify.com",
        "captcha_type": "recaptcha",  # Force type
        "detect_from_page": False
    }
)
```

---

## 🎯 Best Practices

1. **Always use auto-detect first** - Let the API find the actual site key
2. **Use /api/v1/solve/auto** - Simplest endpoint for most cases
3. **Cache is automatic** - Repeat requests to same domain are faster
4. **Check response metadata** - See which site key and type was used
5. **Fallback gracefully** - If auto-detect fails, try with manual site key

---

## 📞 Support

- **Support Group:** [StreetFind](https://t.me/streetfind)
- **Owner:** [@DEBRAJ227](https://t.me/deebuchecked)

**Join for help, updates, and new features!**

---

**Made with 🔥 by @DEBRAJ227**  
**Support:** https://t.me/streetfind
