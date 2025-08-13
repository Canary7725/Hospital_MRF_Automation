# selenium_utils.py
import base64
import json
import re
import time
import traceback
import random
import os
from urllib.parse import parse_qs, urljoin, urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False


class SeleniumHandler:
    def __init__(self, headless=True):
        self.headless = headless
        self._init_driver()

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # macOS example

        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-data-dir=/tmp/selenium-profile")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")  # Add this for stability
        chrome_options.add_argument("--disable-web-security")  # Add this for accessing local files
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Faster loading
        chrome_options.add_argument("--disable-javascript")  # Optional: faster loading
        
        # Set timeouts
        chrome_options.add_argument("--timeout=30000")
        chrome_options.add_argument("--page-load-strategy=eager")

        # Set custom user-agent
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
        if self.headless:
            chrome_options.add_argument("--headless")

        try:
            # Try with automatic driver management first
            self.driver = uc.Chrome(options=chrome_options,version_main=139, headless=self.headless, use_subprocess=True)
            # Set timeouts
            self.driver.set_page_load_timeout(60)  # 60 seconds page load timeout
            self.driver.implicitly_wait(10)  # 10 seconds implicit wait
        except Exception as e:
            print(f"Failed to initialize with undetected_chromedriver: {e}")
            print("Falling back to regular ChromeDriver...")
            try:
                # Fallback to regular ChromeDriver with automatic driver management
                if WEBDRIVER_MANAGER_AVAILABLE:
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    # Last fallback - try system ChromeDriver
                    print("webdriver_manager not available. Trying system ChromeDriver...")
                    self.driver = webdriver.Chrome(options=chrome_options)
                
                # Set timeouts for fallback driver too
                self.driver.set_page_load_timeout(60)
                self.driver.implicitly_wait(10)
            except Exception as e2:
                print(f"Failed to initialize with fallback methods: {e2}")
                print("Please install webdriver_manager: pip install webdriver-manager")
                print("Or update your Chrome browser and ChromeDriver to compatible versions")
                raise

    def ensure_driver(self):
        """Ensure the driver is running and responsive"""
        try:
            # Test if driver is responsive
            self.driver.current_url
            # Try a simple operation to test responsiveness
            self.driver.execute_script("return document.readyState")
        except Exception as e:
            print(f"Driver not responsive: {e}. Restarting...")
            try:
                self.driver.quit()
            except:
                pass
            self._init_driver()

    def safe_get(self, url, timeout=60):
        """Safely navigate to a URL with timeout handling"""
        try:
            self.driver.set_page_load_timeout(timeout)
            self.driver.get(url)
            return True
        except Exception as e:
            print(f"Error loading {url}: {e}")
            # Try to stop loading and continue
            try:
                self.driver.execute_script("window.stop();")
            except:
                pass
            return False

    def restart_driver(self):
        """Restart the driver completely"""
        print("Restarting WebDriver...")
        try:
            self.driver.quit()
        except:
            pass
        time.sleep(2)
        self._init_driver()
        print("WebDriver restarted successfully")

    def close(self):
        self.driver.quit()

    def wait_for_page_load(self, timeout=15):
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def human_type(self, element, text, max_retries=3):
        """Type text with human-like delays and retry logic for stale elements"""
        for attempt in range(max_retries):
            try:
                # Clear the element first
                element.clear()
                time.sleep(0.5)
                
                # Type the text character by character
                for char in text:
                    element.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.2))
                return True
                
            except Exception as e:
                if "stale element reference" in str(e).lower() and attempt < max_retries - 1:
                    print(f"Stale element detected, retrying... (attempt {attempt + 1})")
                    time.sleep(1)
                    # Try to find the element again
                    try:
                        element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.NAME, 'q'))
                        )
                    except:
                        print("Could not re-find search element")
                        return False
                else:
                    print(f"Error in human_type: {e}")
                    return False
        return False

    def scroll_randomly(self):
        scroll_amount = random.randint(100, 1000)
        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.5, 1.5))

    def is_captcha_present(self):
        try:
            self.driver.find_element(By.XPATH, '//iframe[contains(@src, "recaptcha")]')
            print("CAPTCHA iframe detected.")
            return True
        except NoSuchElementException:
            pass

        try:
            self.driver.find_element(By.XPATH, '//*[contains(text(), "not a robot")]')
            print("CAPTCHA text detected.")
            return True
        except NoSuchElementException:
            pass

        return False

    def url_exists_selenium(self, url, timeout=10):
        """Check if URL exists using Selenium instead of requests"""
        if not url or not url.startswith(('http://', 'https://')):
            return False
            
        current_url = self.driver.current_url
        try:
            self.driver.get(url)
            time.sleep(2)  # Give page time to load
            
            # Check if page loaded successfully
            page_title = self.driver.title.lower()
            page_source = self.driver.page_source.lower()
            
            # Common indicators of failed page loads
            error_indicators = [
                'not found', 'page not found', 'error 404',
                'forbidden', 'access denied',
                'server error', 'internal server error',
                'this page doesn\'t exist', 'page doesn\'t exist',
                'site can\'t be reached', 'connection timed out'
            ]
            
            # Check if any error indicators are present
            for indicator in error_indicators:
                if indicator in page_title or indicator in page_source:
                    return False
            
            # If we get here and have some content, consider it valid
            return True
            
        except Exception as e:
            print(f"Error checking URL {url}: {e}")
            return False
        finally:
            # Try to go back to previous page if possible
            try:
                if current_url and current_url != url:
                    self.driver.get(current_url)
            except:
                pass

    def get_page_content_selenium(self, url, timeout=10):
        """Get page content using Selenium instead of requests"""
        try:
            self.driver.get(url)
            time.sleep(2)
            self.wait_for_page_load(timeout)
            return self.driver.page_source
        except Exception as e:
            print(f"Error fetching content from {url}: {e}")
            return None

    def get_url(self, search_query, max_retries=3):
        for attempt in range(max_retries):
            try:
                self.ensure_driver()
                
                # Use safe_get instead of direct driver.get
                if not self.safe_get("https://www.bing.com", timeout=30):
                    print("Failed to load Bing homepage")
                    if attempt < max_retries - 1:
                        self.restart_driver()
                        continue
                    return None

                self.wait_for_page_load(timeout=10)

                if self.is_captcha_present():
                    print("CAPTCHA detected, taking screenshot...")
                    try:
                        os.makedirs("screenshots", exist_ok=True)
                        self.driver.save_screenshot("screenshots/captcha_detected.png")
                    except:
                        pass
                    return None

                self.scroll_randomly()

                # Find search box with retry logic
                search_box = None
                for search_attempt in range(3):
                    try:
                        search_box = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.NAME, 'q'))
                        )
                        break
                    except TimeoutException:
                        if search_attempt < 2:
                            print(f"Search box not found, retrying... (attempt {search_attempt + 1})")
                            time.sleep(2)
                        else:
                            print("Could not find search box after multiple attempts")
                            if attempt < max_retries - 1:
                                self.restart_driver()
                            return None

                if not search_box:
                    if attempt < max_retries - 1:
                        self.restart_driver()
                        continue
                    return None

                # Clear any existing text and type the search query
                success = self.human_type(search_box, search_query)
                if not success:
                    if attempt < max_retries - 1:
                        print(f"Failed to type search query, retrying... (attempt {attempt + 1})")
                        self.restart_driver()
                        continue
                    else:
                        return None

                search_box.send_keys(Keys.RETURN)
                time.sleep(random.uniform(2, 4))

                if "captcha" in self.driver.current_url or "rv/sr" in self.driver.current_url:
                    print("[BLOCKED] CAPTCHA triggered.")
                    return None

                original_window = self.driver.current_window_handle
                original_tabs = set(self.driver.window_handles)

                try:
                    try:
                        website_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Website' or @aria-label='Website Website']"))
                        )
                    except TimeoutException:
                        website_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Website']"))
                        )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", website_button)
                    time.sleep(random.uniform(1,2))
                    website_button.click()
                    self.wait_for_page_load()
                    new_tabs = set(self.driver.window_handles) - original_tabs
                    if new_tabs:
                        self.driver.switch_to.window(new_tabs.pop())
                    else:
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.wait_for_page_load()
                    website_url = self.driver.current_url

                    if "Page Not Found" not in self.driver.page_source:
                        self.driver.close()
                        self.driver.switch_to.window(original_window)
                        return website_url
                    else:
                        self.driver.close()
                        self.driver.switch_to.window(original_window)
                except Exception:
                    print("No Website button or not clickable.")

                try:
                    print("searching for first link in search page")
                    try:
                        link_elem = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.b_tpcn a"))
                        )
                    except TimeoutException:
                        link_elem = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "li.b_algo h2 a"))
                        )
                    link = link_elem.get_attribute("href")
                    if link.startswith('https://www.bing.com'):
                        print("Decoding bing redirect link")
                        link = extract_url_from_bing_redirect(link)
                        print(f"search page first link returned:{link}")
                    
                    # Use Selenium to check if URL exists instead of requests
                    if self.url_exists_selenium(link):
                        return link
                except Exception:
                    pass

                return None

            except Exception as e:
                print(f"Attempt {attempt + 1} failed with error: {e}")
                if "timeout" in str(e).lower() or "connection" in str(e).lower():
                    print("Connection/timeout error detected. Restarting driver...")
                    self.restart_driver()
                
                if attempt < max_retries - 1:
                    print(f"Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    print("All retry attempts failed")
                    traceback.print_exc()
                    return None
        
        return None
        
    def get_source_mrf_manually(self, url, search_query):
        try:
            self.ensure_driver()
            self.driver.get(url)
            time.sleep(5)
            self.wait_for_page_load() 
            price_transparency_link = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//a[.//text()["
                    "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'price') or "
                    "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'pricing') or "
                    "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'transparency')]]"
                )))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", price_transparency_link)
            print(price_transparency_link.get_attribute('href'))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", price_transparency_link)
            self.driver.execute_script("arguments[0].click();", price_transparency_link)
            self.wait_for_page_load()
            source_url = price_transparency_link.get_attribute('href')
            search_words = normalize_to_keywords("standardcharges transparency mrf standard charges chargemaster charge master")
            try:
                WebDriverWait(self.driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))
                all_links = self.driver.find_elements(By.TAG_NAME, "a")

                best_match = None
                best_score = 0

                for link in all_links:
                    href = link.get_attribute("href")
                    if href:
                        href_words = tokenize_href(href)
                        match_score = len(search_words.intersection(href_words))

                        if match_score > best_score:
                            best_score = match_score
                            best_match = urljoin(self.driver.current_url, href)
                if not best_match:
                    print("Mrf link not found")
            except Exception as e:
                print('Error', e)
                return source_url, "MRF Link Not Found"
            return source_url, best_match
        except Exception:
            print("Price Transparency Not Found")
            return "Price Transparency Not Found", None


def normalize_to_keywords(text):
    text = re.sub(r"[^\w\s]", " ", text.lower())  # replace punctuation with space
    return set(text.split())


def tokenize_href(href):
    # Replace separators with space and normalize
    tokens = re.sub(r"[\/_\-\.?=&]", " ", href)  # split on URL separators
    return normalize_to_keywords(tokens)


def extract_url_from_bing_redirect(url):
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if 'u' in params:
            encoded_url = params['u'][0]
            if encoded_url.startswith('a1'):
                encoded_url = encoded_url[2:]
            decoded_bytes = base64.b64decode(encoded_url + '==')
            return decoded_bytes.decode('utf-8')
        return None
    except Exception as e:
        print(f"Error extracting URL: {e}")
        return None


