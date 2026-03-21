# CxC Checker with Built-in Captcha Solver

## Overview
This is the CxC AutoShopify checker with **built-in captcha solving** - no external API dependency required!

## Features
- ✅ **Auto-detect captcha** from Shopify store pages (reCAPTCHA v2/v3, hCaptcha)
- ✅ **Auto-solve captcha** with retry logic (max 3 retries, 2s delays)
- ✅ **Find cheapest product** automatically
- ✅ **Add to cart + create checkout**
- ✅ **Tokenize credit card**
- ✅ **Complete checkout flow** with delivery expectations
- ✅ **Proxy support** (http, https, socks)
- ✅ **Full error handling & logging**

## Configuration

### Enable/Disable Captcha Solver
```python
CAPTCHA_SOLVER_ENABLED = True  # Set to False to disable captcha solving
MAX_CAPTCHA_RETRIES = 3        # Maximum retry attempts
CAPTCHA_RETRY_DELAY = 2        # Delay between retries (seconds)
```

## API Usage

### Endpoint: `/process`

**Format:**
```
GET /process?key=API_KEY&cc=CC_DATA&site=SHOP_URL&proxy=PROXY
```

**Parameters:**
- `key` - API key (default: `md-tech`)
- `cc` - Card data in format `cc|mm|yy|cvv`
- `site` - Shopify store URL or product URL
- `proxy` - Proxy in format `host:port:user:pass` or `host:port`

**Example:**
```bash
curl "http://localhost:5000/process?key=md-tech&cc=4342580222985194|04|28|000&site=https://example.myshopify.com&proxy=pl-tor.pvdata.host:8080:g2rTXpNfPdcw2fzGtWKp62yH:nizar1elad2"
```

**Response:**
```json
{
  "status": "Approved",
  "site": "Working",
  "amount": "$25.00 USD",
  "response": "Charged Successfully",
  "proxy": "Working",
  "captcha_solved": true,
  "captcha_token": "2dR5x...truncated"
}
```

## Captcha Solving Process

1. **Detection**: Scrapes the Shopify store page to detect captcha type and site key
2. **Solving**: 
   - **reCAPTCHA v2**: Uses Google anchor/reload method
   - **hCaptcha**: Uses hCaptcha API
3. **Retry Logic**: Up to 3 attempts with 2-second delays
4. **Integration**: Captcha token automatically applied to checkout session

## Supported Captcha Types
- ✅ reCAPTCHA v2 (visible & invisible)
- ✅ reCAPTCHA v3
- ✅ hCaptcha
- ⚠️ Cloudflare Turnstile (coming soon)

## Deployment

### Railway
1. Create new project from GitHub
2. Select `cxc-checker-captcha-integrated.py`
3. Set environment variables:
   - `PORT=5000`
4. Deploy!

### Local
```bash
python cxc-checker-captcha-integrated.py
```

Server runs on `http://localhost:5000`

## Requirements
```
flask
requests
beautifulsoup4
```

Install:
```bash
pip install flask requests beautifulsoup4
```

## Support
Telegram: https://t.me/streetfind

## Notes
- Captcha solving is **built-in** - no external API needed!
- Works with any Shopify store
- Automatically finds cheapest product if no product URL provided
- Proxy rotation recommended for high-volume checking
