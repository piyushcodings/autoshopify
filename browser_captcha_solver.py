"""
Shopify Captcha Solver with Browser Automation
Bypasses advanced bot protection using real browser
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import requests

class BrowserCaptchaSolver:
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.session = requests.Session()
        
    def setup_driver(self):
        """Setup Chrome driver with stealth options"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        # Stealth options
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        # User agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Window size
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Use webdriver-manager to auto-install ChromeDriver for Chromium
        from webdriver_manager.core.os_manager import ChromeType
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def solve_with_browser(self, shop_url, timeout=60):
        """
        Solve captcha using real browser
        Returns captcha token and session cookies
        """
        try:
            if not self.driver:
                self.setup_driver()
            
            # Go to checkout page
            checkout_url = f"{shop_url}/checkout"
            print(f"🌐 Opening checkout: {checkout_url}")
            self.driver.get(checkout_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Check if captcha is present
            captcha_present = False
            
            # Look for reCAPTCHA
            try:
                recaptcha_frame = self.driver.find_element(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
                if recaptcha_frame:
                    captcha_present = True
                    print("🎯 reCAPTCHA detected")
            except:
                pass
            
            # Look for hCaptcha
            try:
                hcaptcha_element = self.driver.find_element(By.CSS_SELECTOR, ".h-captcha")
                if hcaptcha_element:
                    captcha_present = True
                    print("🎯 hCaptcha detected")
            except:
                pass
            
            if not captcha_present:
                print("✅ No captcha found on page")
                # Just get the page cookies
                cookies = self.driver.get_cookies()
                for cookie in cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                return {"success": True, "token": None, "cookies": cookies}
            
            # Wait for captcha to be solvable
            print("⏳ Waiting for captcha...")
            time.sleep(5)
            
            # Get captcha token from page
            captcha_token = self.get_captcha_token()
            
            if captcha_token:
                print(f"✅ Captcha solved! Token: {captcha_token[:30]}...")
                
                # Get all cookies
                cookies = self.driver.get_cookies()
                for cookie in cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                
                return {
                    "success": True,
                    "token": captcha_token,
                    "cookies": cookies,
                    "session": self.session
                }
            else:
                print("⚠️ Could not get captcha token")
                return {"success": False, "error": "No token extracted"}
                
        except Exception as e:
            print(f"❌ Browser solver error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_captcha_token(self):
        """Extract captcha token from page"""
        try:
            # Try to get token from localStorage
            token = self.driver.execute_script("return localStorage.getItem('_captcha_token');")
            if token:
                return token
            
            # Try to get from window object
            token = self.driver.execute_script("return window.captchaToken;")
            if token:
                return token
            
            # Try to find in page source
            page_source = self.driver.page_source
            token_match = re.search(r'"recaptchaToken"\s*:\s*"([^"]+)"', page_source)
            if token_match:
                return token_match.group(1)
            
            # Try reCAPTCHA response iframe
            try:
                self.driver.switch_to.default_content()
                recaptcha_challenge = self.driver.find_element(By.CSS_SELECTOR, "#recaptcha-token")
                if recaptcha_challenge:
                    return recaptcha_challenge.get_attribute("value")
            except:
                pass
            
            return None
        except Exception as e:
            print(f"Token extraction error: {e}")
            return None
    
    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None


# Test function
if __name__ == "__main__":
    solver = BrowserCaptchaSolver(headless=False)
    
    try:
        result = solver.solve_with_browser("https://eternal-tattoo-supply.myshopify.com")
        print(f"\nResult: {result}")
    finally:
        solver.close()
