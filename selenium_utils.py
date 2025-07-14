# selenium_utils.py
import base64
import json
import re
import time
import traceback
import random
import requests
from urllib.parse import parse_qs, urljoin, urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class SeleniumHandler:
    def __init__(self, headless=True):
        chrome_options = Options()
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        if headless:
            chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome(service=Service(), options=chrome_options)
    
    def ensure_driver(self):
        if self.driver.service.process is None:
            print("WebDriver is not running. Restarting...")
            self.__init__(headless=True)


    def close(self):
        self.driver.quit()

    def wait_for_page_load(self, timeout=30):
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def human_type(self, element, text):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))

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

    def get_url(self, search_query):
        try:
            self.ensure_driver()
            self.driver.get("https://www.bing.com")
            self.wait_for_page_load()

            if self.is_captcha_present():
                self.driver.save_screenshot("captcha_detected.png")
                return None

            self.scroll_randomly()

            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, 'q'))
            )
            self.human_type(search_box, search_query)
            search_box.send_keys(Keys.RETURN)

            time.sleep(random.uniform(2, 4))
            self.scroll_randomly()

            if "captcha" in self.driver.current_url or "rv/sr" in self.driver.current_url:
                print("[BLOCKED] CAPTCHA triggered.")
                return None

            original_window = self.driver.current_window_handle
            original_tabs = set(self.driver.window_handles)

            try:
                website_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Website' or normalize-space(text())='Website']"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", website_button)
                time.sleep(random.uniform(1,2))
                website_button.click()
                new_tabs = set(self.driver.window_handles) - original_tabs
                self.wait_for_page_load()
                if new_tabs:
                    self.driver.switch_to.window(new_tabs.pop())
                else:
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                website_url = self.driver.current_url
                self.driver.close()
                self.driver.switch_to.window(original_window)

                if url_exists(website_url):
                    return website_url
                else:
                    self.driver.close
                    self.driver.switch_to.window(original_window)
            except Exception:
                print("No Website button or not clickable.")

            try:
                link_elem = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.b_algo h2 a"))
                )
                link = link_elem.get_attribute("href")
                if link.startswith('https://www.bing.com'):
                    print("Decoding bing redirect link")
                    link = extract_url_from_bing_redirect(link)
                if url_exists(link):
                    return link
            except Exception:
                pass

            return None

        except Exception:
            traceback.print_exc()
            return None
        
    def get_soruce_mrf_manually(self,url,search_query):
        try:
            self.ensure_driver()
            self.driver.get(url)
            price_transparency_link=WebDriverWait(self.driver,10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[normalize-space(text())='Price Transparency']"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", price_transparency_link)
            price_transparency_link.click()
            source_url=self.driver.current_url
            search_words = normalize_to_keywords(search_query) | normalize_to_keywords("standardcharges transparency mrf standard charges chargemaster charge master")
            try:
                WebDriverWait(self.driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))
                all_links = self.driver.find_elements(By.TAG_NAME, "a")

                best_match=None
                best_score=0

                for link in all_links:
                    href=link.get_attribute("href")
                    if href:
                        href_words=tokenize_href(href)
                        match_score=len(search_words.intersection(href_words))

                        if match_score>best_score:
                            best_score = match_score
                            best_match = urljoin(self.driver.current_url, href)
                
                if not best_match:
                    print("Mrf link not found")
            except Exception as e:
                print('Error',e)
            return source_url,best_match
        except Exception:
            print("Price Transparency Not Found")
            return "Price Transparency Not Found",None
    

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

def url_exists(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.5735.110 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False
