"""
Shopify Universal Captcha Solver - Python Client Library
Solves: reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile
Support: https://t.me/streetfind
"""

import requests
import time
from typing import Optional, Dict, List


class CaptchaSolver:
    """Universal Client for Shopify Captcha Solver API"""
    
    def __init__(self, api_key: str, base_url: str = "https://your-app.railway.app"):
        """
        Initialize Captcha Solver
        
        Args:
            api_key: Your API key
            base_url: API base URL
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "User-Agent": "CaptchaSolver/2.0"
        })
    
    def solve(self, site_key: str,
              page_url: str = "https://example.com",
              captcha_type: str = "auto",
              invisible: bool = True,
              max_retries: int = 5) -> Optional[str]:
        """
        Universal captcha solver - auto-detects and solves any captcha type
        
        Args:
            site_key: Captcha site key
            page_url: URL where captcha appears
            captcha_type: recaptcha, hcaptcha, turnstile, or auto
            invisible: Whether it's invisible reCAPTCHA
            max_retries: Maximum retry attempts
        
        Returns:
            Captcha token or None if failed
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/solve",
                json={
                    "site_key": site_key,
                    "page_url": page_url,
                    "captcha_type": captcha_type,
                    "invisible": invisible,
                    "max_retries": max_retries
                },
                timeout=30
            )
            
            result = response.json()
            
            if result.get("success"):
                return result["token"]
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        
        return None
    
    def solve_recaptcha(self, site_key: str = "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
                        page_url: str = "https://example.com",
                        invisible: bool = True,
                        max_retries: int = 5) -> Optional[str]:
        """
        Solve reCAPTCHA v2/v3
        
        Args:
            site_key: reCAPTCHA site key
            page_url: URL where captcha appears
            invisible: Whether it's invisible reCAPTCHA
            max_retries: Maximum retry attempts
        
        Returns:
            Captcha token or None if failed
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/solve/recaptcha",
                json={
                    "site_key": site_key,
                    "page_url": page_url,
                    "invisible": invisible,
                    "max_retries": max_retries
                },
                timeout=30
            )
            
            result = response.json()
            
            if result.get("success"):
                return result["token"]
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        
        return None
    
    def solve_hcaptcha(self, site_key: str = "f5061357-1d10-4b83-b7a9-7c5f5c5f5c5f",
                       page_url: str = "https://example.com",
                       max_retries: int = 3) -> Optional[str]:
        """
        Solve hCaptcha
        
        Args:
            site_key: hCaptcha site key
            page_url: URL where captcha appears
            max_retries: Maximum retry attempts
        
        Returns:
            Captcha token or None if failed
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/solve/hcaptcha",
                json={
                    "site_key": site_key,
                    "page_url": page_url,
                    "max_retries": max_retries
                },
                timeout=30
            )
            
            result = response.json()
            
            if result.get("success"):
                return result["token"]
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        
        return None
    
    def solve_turnstile(self, site_key: str = "1x00000000000000000000AA",
                        page_url: str = "https://example.com",
                        max_retries: int = 3) -> Optional[str]:
        """
        Solve Cloudflare Turnstile
        
        Args:
            site_key: Turnstile site key
            page_url: URL where captcha appears
            max_retries: Maximum retry attempts
        
        Returns:
            Captcha token or None if failed
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/solve/turnstile",
                json={
                    "site_key": site_key,
                    "page_url": page_url,
                    "max_retries": max_retries
                },
                timeout=30
            )
            
            result = response.json()
            
            if result.get("success"):
                return result["token"]
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        
        return None
    
    def solve_shopify(self, site_key: str = "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",
                      page_url: str = "https://checkout.shopify.com",
                      invisible: bool = True,
                      max_retries: int = 5) -> Optional[str]:
        """
        Specialized Shopify captcha solver
        Optimized for all Shopify store variants
        
        Args:
            site_key: reCAPTCHA site key
            page_url: Shopify URL
            invisible: Whether it's invisible reCAPTCHA
            max_retries: Maximum retry attempts (higher for Shopify)
        
        Returns:
            Captcha token or None if failed
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/solve/shopify",
                json={
                    "site_key": site_key,
                    "page_url": page_url,
                    "invisible": invisible,
                    "max_retries": max_retries
                },
                timeout=30
            )
            
            result = response.json()
            
            if result.get("success"):
                return result["token"]
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        
        return None
    
    def solve_with_retry(self, site_key: str,
                         page_url: str = "https://example.com",
                         captcha_type: str = "auto",
                         max_attempts: int = 3) -> Optional[str]:
        """
        Solve captcha with multiple attempts
        
        Args:
            site_key: Captcha site key
            page_url: URL where captcha appears
            captcha_type: Type of captcha
            max_attempts: Maximum solve attempts
        
        Returns:
            Captcha token or None if failed
        """
        for attempt in range(max_attempts):
            token = self.solve(site_key, page_url, captcha_type)
            if token:
                return token
            if attempt < max_attempts - 1:
                time.sleep(2)
        return None
    
    def get_site_keys(self) -> Dict:
        """Get all available site keys from API"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/sitekeys",
                timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"Site keys error: {e}")
            return {}
    
    def verify_token(self, token: str, captcha_type: str = "recaptcha") -> Dict:
        """
        Verify captcha token format
        
        Args:
            token: Captcha token to verify
            captcha_type: Type of captcha
        
        Returns:
            Verification result
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/verify",
                json={
                    "token": token,
                    "captcha_type": captcha_type
                },
                timeout=10
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def health_check(self) -> Dict:
        """Check API health status"""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_stats(self) -> Optional[Dict]:
        """Get API usage statistics"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/stats",
                timeout=5
            )
            return response.json()
        except Exception as e:
            print(f"Stats error: {e}")
            return None


# Common site keys for different services
SHOPIFY_SITE_KEYS = [
    "6LfLB8oZAAAAACdFNV7uq5znzqoNt2-VYujiN15d",  # Primary Shopify
    "6Lc4FowfAAAAAPiXf6lyEPAe_84kesFIGdJUdRTe",  # Spotify/Shopify
    "6LeGq8kZAAAAABKt4RjZJq8xJz9xJz9xJz9xJz9x",  # Generic Shopify
]

HCAPTCHA_SITE_KEYS = [
    "f5061357-1d10-4b83-b7a9-7c5f5c5f5c5f",
    "f5061358-1d10-4b83-b7a9-7c5f5c5f5c5f",
]

TURNSTILE_SITE_KEYS = [
    "1x00000000000000000000AA",
    "2x00000000000000000000AA",
]


# Example usage
if __name__ == "__main__":
    # Initialize solver
    solver = CaptchaSolver(
        api_key="DARK-STORMX-DEEPX",
        base_url="https://your-app.railway.app"
    )
    
    print("=" * 60)
    print("🚀 Shopify Universal Captcha Solver v2.0")
    print("📞 Support: https://t.me/streetfind")
    print("=" * 60)
    print()
    
    # Health check
    print("🏓 Health Check:")
    health = solver.health_check()
    print(f"   Status: {health.get('status', 'Unknown')}")
    print(f"   Version: {health.get('version', 'Unknown')}")
    print(f"   Captcha Types: {', '.join(health.get('captcha_types', []))}")
    print()
    
    # Test reCAPTCHA (Shopify)
    print("🔑 Testing reCAPTCHA (Shopify)...")
    for site_key in SHOPIFY_SITE_KEYS:
        token = solver.solve_shopify(site_key, "https://checkout.shopify.com")
        if token:
            print(f"   ✅ Success! Site Key: {site_key[:20]}...")
            print(f"   Token: {token[:50]}...")
            print(f"   Length: {len(token)}")
            break
        else:
            print(f"   ⏳ Trying next site key...")
    else:
        print("   ❌ All Shopify site keys failed")
    print()
    
    # Test hCaptcha
    print("🔑 Testing hCaptcha...")
    for site_key in HCAPTCHA_SITE_KEYS:
        token = solver.solve_hcaptcha(site_key, "https://example.com")
        if token:
            print(f"   ✅ Success! Token: {token[:50]}...")
            break
    else:
        print("   ❌ hCaptcha solving failed")
    print()
    
    # Test Turnstile
    print("🔑 Testing Cloudflare Turnstile...")
    for site_key in TURNSTILE_SITE_KEYS:
        token = solver.solve_turnstile(site_key, "https://example.com")
        if token:
            print(f"   ✅ Success! Token: {token[:50]}...")
            break
    else:
        print("   ❌ Turnstile solving failed")
    print()
    
    # Get stats
    print("📊 API Stats:")
    stats = solver.get_stats()
    if stats:
        print(f"   Total Requests: {stats.get('stats', {}).get('total_requests', 'N/A')}")
        print(f"   Unique Users: {stats.get('stats', {}).get('unique_users', 'N/A')}")
        print(f"   Rate Limit: {stats.get('stats', {}).get('rate_limit', 'N/A')}/min")
    print()
    
    # Get site keys
    print("📦 Available Site Keys:")
    site_keys = solver.get_site_keys()
    if site_keys.get('success'):
        counts = site_keys.get('counts', {})
        print(f"   reCAPTCHA: {counts.get('recaptcha', 0)} keys")
        print(f"   hCaptcha: {counts.get('hcaptcha', 0)} keys")
        print(f"   Turnstile: {counts.get('turnstile', 0)} keys")
    print()
    
    print("=" * 60)
    print("✅ Testing Complete!")
    print("📞 Need Help? Join: https://t.me/streetfind")
    print("=" * 60)
