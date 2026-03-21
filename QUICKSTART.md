# 🚀 Quick Start Guide - Deploy in 5 Minutes

Get your Shopify Universal Captcha Solver API running on Railway in under 5 minutes!

---

## Prerequisites

- GitHub account
- Railway account (free tier available)
- Telegram (for support: https://t.me/streetfind)

---

## Step 1: Push to GitHub (2 minutes)

```bash
# Navigate to the API directory
cd shopify-captcha-api

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Shopify Captcha Solver API v2.0"

# Create a new repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/shopify-captcha-api.git
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy to Railway (2 minutes)

### Option A: Direct Deploy (Easiest)

1. Go to [Railway](https://railway.app/)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `shopify-captcha-api` repository
5. Click **"Deploy"**

### Option B: CLI Deploy

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Select your repository
# Choose "Shopify Captcha Solver API"

# Deploy
railway up
```

---

## Step 3: Configure Environment Variables (1 minute)

In Railway Dashboard:

1. Click on your project
2. Go to **"Variables"** tab
3. Add these variables:

```
API_KEY=DARK-STORMX-DEEPX
RATE_LIMIT=60
DEBUG=False
```

**Optional variables:**
```
# For higher rate limits
RATE_LIMIT=120

# For debugging (set to True temporarily)
DEBUG=True
```

---

## Step 4: Get Your URL (30 seconds)

In Railway Dashboard:

1. Go to **"Settings"** tab
2. Click **"Generate Domain"**
3. Copy your URL (e.g., `https://your-app-production.up.railway.app`)

**OR using CLI:**
```bash
railway domain
```

---

## Step 5: Test Your API (30 seconds)

```bash
# Test health endpoint
curl https://your-app.railway.app/health

# Test captcha solving
curl -X POST https://your-app.railway.app/api/v1/solve/shopify \
  -H "Content-Type: application/json" \
  -H "X-API-Key: DARK-STORMX-DEEPX" \
  -d '{
    "site_key": "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
    "page_url": "https://checkout.shopify.com",
    "invisible": true,
    "max_retries": 5
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "token": "03AGdBq...",
  "time_taken": 2.34,
  "attempt": 1
}
```

---

## Step 6: Integrate with Your Bot (Optional)

Add to your bot code:

```python
CAPTCHA_API_URL = "https://your-app.railway.app"
CAPTCHA_API_KEY = "DARK-STORMX-DEEPX"

def get_captcha_token_api(site_key, page_url):
    response = requests.post(
        f"{CAPTCHA_API_URL}/api/v1/solve/shopify",
        headers={"X-API-Key": CAPTCHA_API_KEY},
        json={
            "site_key": site_key,
            "page_url": page_url,
            "invisible": True,
            "max_retries": 5
        },
        timeout=30
    )
    
    if response.json().get("success"):
        return response.json()["token"]
    return None
```

---

## ✅ You're Done!

Your API is now live and ready to solve captchas!

**API Endpoints:**
- Health: `GET https://your-app.railway.app/health`
- Solve: `POST https://your-app.railway.app/api/v1/solve`
- Stats: `GET https://your-app.railway.app/api/v1/stats`

---

## 🔧 Common Issues

### Build Failed
- Check Railway build logs
- Ensure all files are committed
- Verify `requirements.txt` is present

### API Returns 503
- Wait for deployment to complete
- Check Railway dashboard for errors
- Verify environment variables are set

### Rate Limiting
- Default: 60 requests/minute
- Increase in Railway variables: `RATE_LIMIT=120`

### Timeout Errors
- Increase timeout in your requests
- Check Railway region (closer to your users)

---

## 📊 Monitoring

### Railway Dashboard
- View logs in real-time
- Monitor resource usage
- Check deployment history

### API Stats Endpoint
```bash
curl https://your-app.railway.app/api/v1/stats \
  -H "X-API-Key: DARK-STORMX-DEEPX"
```

---

## 🆘 Need Help?

**Support Group:** [StreetFind](https://t.me/streetfind)

- Get integration help
- Report issues
- Request features
- Connect with users

---

## 📈 Scaling Tips

### For High Traffic

1. **Increase Railway Plan**
   - Upgrade to paid plan for more resources

2. **Multiple Instances**
   - Deploy multiple Railway instances
   - Load balance between them

3. **Optimize Rate Limits**
   ```
   RATE_LIMIT=200  # Higher limit
   ```

4. **Enable Caching**
   - Cache tokens for reuse (if applicable)

---

## 🔒 Security Checklist

- ✅ API key is strong and unique
- ✅ HTTPS is enabled (automatic on Railway)
- ✅ Debug mode is OFF in production
- ✅ Rate limiting is enabled
- ✅ Environment variables are set (not hardcoded)

---

## 📝 Next Steps

1. **Test thoroughly** with your specific use case
2. **Monitor usage** via `/api/v1/stats`
3. **Join support group** for updates: https://t.me/streetfind
4. **Consider backup deployment** on another platform

---

**Made with 🔥 by @DEBRAJ227**  
**Support:** https://t.me/streetfind
