# ✅ Railway Deployment Checklist

## 📦 Files Ready:

- [x] `cxc-checker-captcha-integrated.py` - Main app with health endpoint
- [x] `requirements.txt` - All dependencies
- [x] `Procfile` - Gunicorn startup
- [x] `railway.toml` - Railway config
- [x] `.railway.json` - Railway schema
- [x] `nixpacks.toml` - Chrome/Python build config
- [x] `.gitignore` - Ignore sensitive files

---

## 🚀 Deploy Steps:

### 1. Push to GitHub
```bash
cd /home/suraj/githubb/cap/shopify-captcha-api

git add .
git commit -m "Ready for Railway deployment"
git push origin main
```

### 2. Deploy on Railway
1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Choose `shopify-captcha-api` repo
5. Click "Deploy"

### 3. Configure Domain
1. Go to project → Settings → Domains
2. Your Railway domain will show (e.g., `shopify-captcha-api-production.up.railway.app`)
3. Or add custom domain if you have one

### 4. Set Variables
In Railway → Variables, add:
```
PORT=5000
CAPTCHA_SOLVER_ENABLED=true
MAX_CAPTCHA_RETRIES=3
```

### 5. Test Deployment
```bash
# Replace with your Railway URL
RAILWAY_URL="https://your-project.railway.app"

# Health check
curl $RAILWAY_URL/health

# Test checkout
curl "$RAILWAY_URL/process?key=md-tech&cc=4400662138120147|10|27|842&site=https://eternal-tattoo-supply.myshopify.com"
```

---

## ✅ Expected Response:

```json
{
  "amount": "$12.38 USD",
  "captcha_solved": true,
  "captcha_token": "0cAFcWeA...",
  "response": "GENERIC_ERROR",
  "site": "Working",
  "status": "Decline"
}
```

---

## 🎯 Your Railway Domain:

Once deployed, your API will be at:
```
https://YOUR_PROJECT_NAME-production.up.railway.app
```

Example:
```
https://shopify-captcha-api-production.up.railway.app
```

---

## 📊 Monitor:

- **Logs**: Railway Dashboard → Logs
- **Metrics**: Railway Dashboard → Metrics  
- **Domain**: Railway Dashboard → Domains

---

## 🔧 Troubleshooting:

### Build Fails:
```bash
# Check Railway logs
# Ensure nixpacks.toml has chromium
```

### Timeout:
```bash
# Increase timeout in Railway settings
# Set to 120 seconds
```

### Chrome Not Found:
```bash
# Verify nixpacks.toml has:
# nixPkgs = ["python311", "chromium", "chromedriver"]
```

---

## ✅ Ready to Deploy!

Push to GitHub and Railway will auto-deploy! 🚀
