# 🚀 Railway Deployment Guide

## ✅ Files Created for Railway:

1. **railway.toml** - Railway configuration
2. **.railway.json** - Railway schema
3. **Procfile** - Gunicorn startup command
4. **requirements.txt** - Updated with all dependencies
5. **.gitignore** - Ignore sensitive files

---

## 📦 Step-by-Step Deployment:

### Step 1: Push to GitHub

```bash
cd /home/suraj/githubb/cap/shopify-captcha-api

# Initialize git if not already done
git init
git add .
git commit -m "Ready for Railway deployment"

# Add your GitHub repo (replace with your repo)
git remote add origin https://github.com/YOUR_USERNAME/shopify-captcha-api.git
git push -u origin main
```

### Step 2: Deploy to Railway

1. **Go to Railway**: https://railway.app
2. **Click "New Project"**
3. **Select "Deploy from GitHub repo"**
4. **Choose your repo**: `shopify-captcha-api`
5. **Click "Deploy"**

### Step 3: Configure Domain

1. **Go to your project settings**
2. **Click "Domains" tab**
3. **Add your domain**:
   - If you have a Railway domain: It will show automatically
   - If you have custom domain: Click "Add Custom Domain"
4. **Copy the generated URL**: `https://your-project.railway.app`

### Step 4: Set Environment Variables

In Railway dashboard, go to **Variables** and add:

```bash
PORT=5000
HOST=0.0.0.0
CAPTCHA_SOLVER_ENABLED=true
MAX_CAPTCHA_RETRIES=3
```

### Step 5: Configure Build

Railway will auto-detect Python. If needed, set:

```bash
# In Railway Variables
PYTHON_VERSION=3.11
```

---

## 🌐 Your API Endpoints:

Once deployed, your API will be available at:

```
https://YOUR_DOMAIN.railway.app/process?key=md-tech&cc=...&site=...
https://YOUR_DOMAIN.railway.app/health
```

---

## 🔧 Testing Deployment:

### 1. Check Health:
```bash
curl https://YOUR_DOMAIN.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "captcha_solver": "enabled"
}
```

### 2. Test Checkout:
```bash
curl "https://YOUR_DOMAIN.railway.app/process?key=md-tech&cc=4400662138120147|10|27|842&site=https://eternal-tattoo-supply.myshopify.com"
```

---

## ⚙️ Advanced Configuration:

### Increase Timeout (for browser solver):

In Railway dashboard → Settings → Advanced:
```
Timeout: 120 seconds
```

### Add More Workers:

Edit `Procfile`:
```
web: gunicorn cxc-checker-captcha-integrated:app --bind 0.0.0.0:$PORT --workers 8 --timeout 120
```

### Enable Browser Solver:

Railway needs Chrome installed. Add `nixpacks.toml`:

```toml
[phases.setup]
nixPkgs = ["chromium", "chromedriver"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[phases.build]
cmds = ["echo 'Building...'"]

[start]
cmd = "gunicorn cxc-checker-captcha-integrated:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120"
```

---

## 📊 Monitoring:

### Railway Dashboard:
- **Logs**: Real-time server logs
- **Metrics**: CPU, Memory, Request count
- **Deployments**: Version history

### Health Check:
```bash
curl https://YOUR_DOMAIN.railway.app/health
```

---

## 🔒 Security:

### Add API Key Protection:

Edit `process_api()` in `cxc-checker-captcha-integrated.py`:

```python
# Add this at the top
API_KEY = os.environ.get("API_KEY", "md-tech")

# In process_api()
if key != API_KEY:
    return jsonify({"error": "Invalid API key"}), 401
```

Then set in Railway Variables:
```bash
API_KEY=your_secure_key_here
```

---

## 💰 Railway Pricing:

- **Free Tier**: $5 credit/month
- **Hobby**: $5/month + usage
- **Pro**: Custom pricing

Your app should run within free tier for moderate usage!

---

## 🎯 Quick Deploy Commands:

```bash
# 1. Commit changes
git add .
git commit -m "Deploy to Railway"
git push origin main

# 2. Railway will auto-deploy!
# Check logs at: https://railway.app/dashboard/YOUR_PROJECT
```

---

## ✅ Post-Deployment Checklist:

- [ ] Health endpoint responds
- [ ] Domain is configured
- [ ] Environment variables are set
- [ ] Test with real shop URL
- [ ] Check logs for errors
- [ ] Monitor resource usage

---

## 🆘 Troubleshooting:

### "Build Failed":
- Check Railway logs for errors
- Ensure `requirements.txt` has all dependencies
- Verify Python version is 3.11+

### "Timeout Errors":
- Increase timeout in Railway settings
- Reduce number of workers
- Check if shop is responding

### "Captcha Not Solving":
- Enable browser solver (add Chrome to build)
- Check logs for captcha detection messages
- Verify shop actually has captcha

---

## 📞 Support:

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Bot Support: https://t.me/streetfind

---

**Ready to deploy! 🚀**

Your Railway app will be at: `https://YOUR_PROJECT.railway.app`
