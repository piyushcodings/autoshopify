# 🚀 Shopify Universal Captcha Solver API v2.0

**SOLVES ALL SHOPIFY CAPTCHAS** - reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile

**Author:** [@DEBRAJ227](https://t.me/deebuchecked)  
**Support Group:** [StreetFind](https://t.me/streetfind)  
**Telegram:** https://t.me/streetfind

---

## 📋 Features

### ✅ All Captcha Types Supported

| Captcha Type | Status | Endpoint |
|--------------|--------|----------|
| **reCAPTCHA v2 (Visible)** | ✅ Supported | `/api/v1/solve/recaptcha` |
| **reCAPTCHA v2 (Invisible)** | ✅ Supported | `/api/v1/solve/recaptcha` |
| **reCAPTCHA v3** | ✅ Supported | `/api/v1/solve/recaptcha` |
| **hCaptcha** | ✅ Supported | `/api/v1/solve/hcaptcha` |
| **Cloudflare Turnstile** | ✅ Supported | `/api/v1/solve/turnstile` |

### 🔥 Advanced Features

- ✅ **Auto-Detection** - Automatically detects captcha type from URL
- ✅ **Multiple Site Keys** - 30+ reCAPTCHA keys, 8+ hCaptcha keys, 3+ Turnstile keys
- ✅ **Smart Retry Logic** - Up to 5 retries with different strategies
- ✅ **User-Agent Rotation** - Avoids detection with 8+ browser profiles
- ✅ **Session Pooling** - Reusable connections for faster responses
- ✅ **Rate Limiting** - Configurable per-IP limits
- ✅ **API Key Authentication** - Secure access control
- ✅ **Health Checks** - Monitor service status
- ✅ **Statistics Endpoint** - Track usage and performance

---

## 🚀 Deploy to Railway

### Option 1: One-Click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/new)

### Option 2: Manual Deploy

```bash
# Clone repository
git clone https://github.com/yourusername/shopify-captcha-api.git
cd shopify-captcha-api

# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway variables set API_KEY=DARK-STORMX-DEEPX
railway variables set RATE_LIMIT=60
railway variables set DEBUG=False
railway up

# Get your URL
railway domain
```

---

## 📖 API Endpoints

### Base URL
```
https://your-app.railway.app
```

### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Shopify Universal Captcha Solver API",
  "version": "2.0.0",
  "author": "@DEBRAJ227",
  "support": "https://t.me/streetfind",
  "captcha_types": ["recaptcha_v2", "recaptcha_v3", "hcaptcha", "turnstile"]
}
```

---

### 2. Universal Captcha Solver (Auto-Detect)
```http
POST /api/v1/solve
Content-Type: application/json
X-API-Key: YOUR_API_KEY
```

**Request Body:**
```json
{
  "site_key": "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
  "page_url": "https://checkout.shopify.com",
  "captcha_type": "auto",
  "invisible": true,
  "max_retries": 5
}
```

**Success Response:**
```json
{
  "success": true,
  "token": "03AGdBq...long_token_here...xyz",
  "site_key": "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
  "page_url": "https://checkout.shopify.com",
  "captcha_type": "recaptcha",
  "invisible": true,
  "time_taken": 2.34,
  "timestamp": 1710934800.123,
  "attempt": 1
}
```

---

### 3. Shopify Specialized Endpoint
```http
POST /api/v1/solve/shopify
Content-Type: application/json
X-API-Key: YOUR_API_KEY
```

**Request Body:**
```json
{
  "site_key": "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
  "page_url": "https://checkout.shopify.com",
  "invisible": true,
  "max_retries": 5
}
```

**Note:** Optimized for Shopify stores with higher retry count and smart site key selection.

---

### 4. reCAPTCHA Dedicated Endpoint
```http
POST /api/v1/solve/recaptcha
Content-Type: application/json
X-API-Key: YOUR_API_KEY
```

**Request Body:**
```json
{
  "site_key": "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
  "page_url": "https://example.com",
  "invisible": true,
  "max_retries": 5
}
```

---

### 5. hCaptcha Dedicated Endpoint
```http
POST /api/v1/solve/hcaptcha
Content-Type: application/json
X-API-Key: YOUR_API_KEY
```

**Request Body:**
```json
{
  "site_key": "f5061357-1d10-4b83-b7a9-7c5f5c5f5c5f",
  "page_url": "https://example.com",
  "max_retries": 3
}
```

---

### 6. Cloudflare Turnstile Endpoint
```http
POST /api/v1/solve/turnstile
Content-Type: application/json
X-API-Key: YOUR_API_KEY
```

**Request Body:**
```json
{
  "site_key": "1x00000000000000000000AA",
  "page_url": "https://example.com",
  "max_retries": 3
}
```

---

### 7. Get All Site Keys
```http
GET /api/v1/sitekeys
X-API-Key: YOUR_API_KEY
```

**Response:**
```json
{
  "success": true,
  "site_keys": {
    "recaptcha": ["6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d", ...],
    "hcaptcha": ["f5061357-1d10-4b83-b7a9-7c5f5c5f5c5f", ...],
    "turnstile": ["1x00000000000000000000AA", ...]
  },
  "counts": {
    "recaptcha": 30,
    "hcaptcha": 8,
    "turnstile": 3
  }
}
```

---

### 8. Verify Token
```http
POST /api/v1/verify
Content-Type: application/json
X-API-Key: YOUR_API_KEY
```

**Request Body:**
```json
{
  "token": "03AGdBq...token_here",
  "captcha_type": "recaptcha"
}
```

---

### 9. API Statistics
```http
GET /api/v1/stats
X-API-Key: YOUR_API_KEY
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_requests": 1523,
    "unique_users": 45,
    "rate_limit": 60,
    "debug_mode": false,
    "supported_captcha_types": ["recaptcha_v2", "recaptcha_v3", "hcaptcha", "turnstile"],
    "site_keys_available": {
      "recaptcha": 30,
      "hcaptcha": 8,
      "turnstile": 3
    }
  }
}
```

---

## 💻 Usage Examples

### Python - Universal Solver
```python
import requests

API_URL = "https://your-app.railway.app"
API_KEY = "DARK-STORMX-DEEPX"

def solve_captcha(site_key, page_url, captcha_type="auto"):
    headers = {"X-API-Key": API_KEY}
    payload = {
        "site_key": site_key,
        "page_url": page_url,
        "captcha_type": captcha_type,
        "invisible": True,
        "max_retries": 5
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/solve",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    result = response.json()
    
    if result.get("success"):
        return result["token"]
    else:
        raise Exception(result.get("error"))

# Shopify Checkout
token = solve_captcha(
    "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
    "https://checkout.shopify.com"
)
print(f"Token: {token[:50]}...")

# hCaptcha
token = solve_captcha(
    "f5061357-1d10-4b83-b7a9-7c5f5c5f5c5f",
    "https://example.com",
    captcha_type="hcaptcha"
)
print(f"hCaptcha Token: {token}")
```

### Python - Integration with Your CC Bot
```python
# Add to your existing bot
CAPTCHA_API_URL = "https://your-app.railway.app"
CAPTCHA_API_KEY = "DARK-STORMX-DEEPX"

def get_captcha_token_api(site_key="6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d", 
                          page_url="https://accounts.spotify.com"):
    """Universal captcha solver - works with ALL Shopify captchas"""
    try:
        response = requests.post(
            f"{CAPTCHA_API_URL}/api/v1/solve/shopify",
            headers={
                "X-API-Key": CAPTCHA_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "site_key": site_key,
                "page_url": page_url,
                "invisible": True,
                "max_retries": 5
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"✅ Captcha solved via API in {data.get('time_taken', 'N/A')}s (Attempt {data.get('attempt', 1)})")
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
    # ... your existing code ...
    
    # Get captcha token using universal API
    captcha_token = get_captcha_token_api()
    if captcha_token:
        # Use token in your request
        pass
    
    # ... rest of your code ...
```

### Node.js
```javascript
const axios = require('axios');

const API_URL = 'https://your-app.railway.app';
const API_KEY = 'DARK-STORMX-DEEPX';

async function solveCaptcha(siteKey, pageUrl, captchaType = 'auto') {
    try {
        const response = await axios.post(
            `${API_URL}/api/v1/solve`,
            {
                site_key: siteKey,
                page_url: pageUrl,
                captcha_type: captchaType,
                invisible: true,
                max_retries: 5
            },
            {
                headers: { 'X-API-Key': API_KEY },
                timeout: 30000
            }
        );
        
        if (response.data.success) {
            return response.data.token;
        } else {
            throw new Error(response.data.error);
        }
    } catch (error) {
        console.error('Captcha solve failed:', error.message);
        throw error;
    }
}

// Usage - Shopify
solveCaptcha('6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d', 'https://checkout.shopify.com')
    .then(token => console.log('Shopify Token:', token.substring(0, 50) + '...'))
    .catch(err => console.error(err));

// Usage - hCaptcha
solveCaptcha('f5061357-1d10-4b83-b7a9-7c5f5c5f5c5f', 'https://example.com', 'hcaptcha')
    .then(token => console.log('hCaptcha Token:', token))
    .catch(err => console.error(err));
```

### cURL
```bash
# Universal solver (auto-detect)
curl -X POST https://your-app.railway.app/api/v1/solve \
  -H "Content-Type: application/json" \
  -H "X-API-Key: DARK-STORMX-DEEPX" \
  -d '{
    "site_key": "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
    "page_url": "https://checkout.shopify.com",
    "captcha_type": "auto",
    "invisible": true,
    "max_retries": 5
  }'

# Shopify specialized
curl -X POST https://your-app.railway.app/api/v1/solve/shopify \
  -H "Content-Type: application/json" \
  -H "X-API-Key: DARK-STORMX-DEEPX" \
  -d '{
    "site_key": "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
    "page_url": "https://checkout.shopify.com",
    "invisible": true,
    "max_retries": 5
  }'

# hCaptcha
curl -X POST https://your-app.railway.app/api/v1/solve/hcaptcha \
  -H "Content-Type: application/json" \
  -H "X-API-Key: DARK-STORMX-DEEPX" \
  -d '{
    "site_key": "f5061357-1d10-4b83-b7a9-7c5f5c5f5c5f",
    "page_url": "https://example.com",
    "max_retries": 3
  }'
```

---

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `DARK-STORMX-DEEPX` | API authentication key |
| `RATE_LIMIT` | `60` | Requests per minute per IP |
| `DEBUG` | `False` | Enable debug logging |
| `PORT` | `5000` | Server port (auto-set by Railway) |

---

## 📊 Site Keys Database

### reCAPTCHA Keys (30+)
- Primary Shopify: `6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d`
- Spotify: `6Lc4FowfAAAAAPiXf6lyEPAe_84kesFIGdJUdRTe`
- And 28+ more for maximum coverage

### hCaptcha Keys (8+)
- Common: `f5061357-1d10-4b83-b7a9-7c5f5c5f5c5f`
- And 7+ more variants

### Turnstile Keys (3+)
- Default: `1x00000000000000000000AA`
- And 2+ more

---

## 📝 Error Codes

| Error | Description | Solution |
|-------|-------------|----------|
| `401` | Invalid or missing API key | Check your API key |
| `429` | Rate limit exceeded | Wait or increase limit |
| `500` | Captcha solving failed | Try different site key or URL |
| `503` | Service unavailable | Check Railway status |

---

## 🔒 Security Best Practices

- ✅ Always use HTTPS in production
- ✅ Rotate API keys regularly
- ✅ Don't expose API keys in client-side code
- ✅ Use environment variables for sensitive data
- ✅ Implement rate limiting per user

---

## 🛠️ Troubleshooting

### API Returns 401
```python
# Make sure you're sending the API key correctly
headers = {"X-API-Key": "DARK-STORMX-DEEPX"}
```

### API Returns 429 (Rate Limit)
```python
# Increase rate limit in Railway environment variables
# RATE_LIMIT=120 (or higher)
```

### Captcha Still Failing
```python
# Try different site keys
site_keys = [
    "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
    "6Lc4FowfAAAAAPiXf6lyEPAe_84kesFIGdJUdRTe",
    "6LeGq8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x"
]

for key in site_keys:
    token = solve_captcha(key, page_url)
    if token:
        break
```

### Timeout Errors
```python
# Increase timeout and retries
payload = {
    "max_retries": 5,  # More retries
}
response = requests.post(url, json=payload, timeout=60)  # Longer timeout
```

---

## 📞 Support

- **Support Group:** [StreetFind](https://t.me/streetfind)
- **Owner:** [@DEBRAJ227](https://t.me/deebuchecked)
- **Channel:** [Deebu Checked](https://t.me/deebuchecked)

**Join for updates, support, and new features!**

---

## 📄 License

This project is for educational purposes. Use responsibly and comply with the terms of service of websites you interact with.

---

## ⚠️ Disclaimer

This API is designed for legitimate automation testing and educational purposes only. The developer is not responsible for any misuse of this software. Always ensure you have proper authorization before automating interactions with any website.

**This API does NOT guarantee 100% success rate.** Captcha solving success depends on various factors including network conditions, captcha complexity, and target website configurations.

---

## 🎯 What Makes This API Different?

1. **Universal Support** - All major captcha types in one API
2. **Smart Auto-Detection** - Automatically detects captcha type
3. **Multiple Site Keys** - 40+ site keys for maximum coverage
4. **Advanced Retry Logic** - Up to 5 retries with different strategies
5. **User-Agent Rotation** - 8+ browser profiles to avoid detection
6. **Session Pooling** - Faster responses with reusable connections
7. **Shopify Optimized** - Specifically tuned for Shopify stores
8. **Active Support** - Join [StreetFind](https://t.me/streetfind) for help

---

**Made with 🔥 by @DEBRAJ227**  
**Support:** https://t.me/streetfind
