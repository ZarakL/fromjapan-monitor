import os
import sys
import time
import json
import glob
import logging
import urllib.parse
import gc
import requests
import atexit
import signal
import subprocess
from datetime import datetime

# Set up logging to a file instead of console output
logging.basicConfig(
    filename='fromjapan_monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Selenium imports 
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# BeautifulSoup for HTML parsing
from bs4 import BeautifulSoup

# Translation library
from deep_translator import GoogleTranslator

# Disable selenium logging
from selenium.webdriver.remote.remote_connection import LOGGER
LOGGER.setLevel(logging.WARNING)

# --- SETTINGS ---
WEBHOOKS = {
    "lizlisa": "https://discord.com/api/webhooks/1356396545213337650/HIMoQICLasRuvHsDq67Sj-LCCxi76s6VUagGHWEEJgwYhX5_HDjiqNmp92F3XGASCDqJ",
    "axesfemme": "https://discord.com/api/webhooks/1356441958318342264/cvUotMmo48zst3_DQFJxy1hVMUgFNJ5CPESFUyFyKmF48b1HiKGdbFJInWLt7ZEyJA_r",
    "lizlisa_nofilter": "https://discord.com/api/webhooks/1356898381288443994/hH-O02qa_k3lF3lrcF5BF0y8nNPstpsSBb72ke_sYBmGLE_Iikjng0zNajDD0pUuV7RV",
    "axesfemme_nofilter": "https://discord.com/api/webhooks/1356898428486946958/WJ74ZUmuAF5PJML3LJAepDMQZZyeCmkJL08FU9eJMoMwbO6-EHZ2d2rjdMit1GXgbeVn"
}
SEARCH_TERMS = {
    "lizlisa": ["リズリサ スカパン", "リズリサ キュロット", "リズリサ ホワイト スカパン", "リズリサ 白 スカパン"],
    "axesfemme": [
        "アクシーズファム ブラウス 茶色",
        "アクシーズファム ブラウス ブラウン",
        "アクシーズファム 茶 ブラウス",
        "アクシーズファム レース ブラウス 茶色",
        "アクシーズファム ブラウス"
    ],
    "lizlisa_nofilter": [
        "リズリサ"
    ],
    "axesfemme_nofilter": [
        "アクシーズファム カットソー",
        "アクシーズファム ブラウス",
        "アクシーズファム 半袖 ブラウス",
        "アクシーズファム レース 半袖 ブラウス",
        "アクシーズファム 半袖 カットソー"
    ]
}
AXESFEMME_EXTRA_KEYWORDS = ["フリル", "リボン", "半袖"]

# Special search terms that don't need keyword filtering
NO_FILTER_TERMS = [
    "リズリサ ホワイト スカパン", 
    "リズリサ 白 スカパン",
    # All lizlisa_nofilter terms
    "リズリサ",
    # All axesfemme_nofilter terms
    "アクシーズファム カットソー",
    "アクシーズファム ブラウス",
    "アクシーズファム 半袖 ブラウス",
    "アクシーズファム レース 半袖 ブラウス",
    "アクシーズファム 半袖 カットソー"
]
BASE_URLS = {
    "mercari": ("https://www.fromjapan.co.jp/japan/en/mercari/search/", "?sort_order=new"),
    "rakuten": ("https://www.fromjapan.co.jp/japan/en/rakuten/search/", "?sort_order=-updateDate"),
    "rakuma":  ("https://www.fromjapan.co.jp/japan/en/rakuma/search/", "?sort_order=new")
}
# Path to ChromeDriver (works with both Chrome and Chromium)
CHROMEDRIVER_PATH = "C:/chromedriver.exe"
# Set to True to use Chromium instead of Chrome if available
USE_CHROMIUM = True
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE = os.path.join(BASE_DIR, "seen_urls.json")

BROWN_KEYWORDS = [
    "brown", "chocolate", "choco", "choco-iro", "mocha", "cocoa", "beige", "tan",
    "ブラウン", "チョコ", "チョコ色", "チョコレート", "モカ", "ココア", "ベージュ", "茶色",
    "リズリサ ブラウン スカパン", "リズリサ 茶色 スカパン", "リズリサ チョコ スカパン",
    "リズリサ ブラウン キュロット", "リズリサ 茶色 キュロット", "リズリサ チョコ キュロット",
    "アクシーズファム ブラウス 茶色", "アクシーズファム ブラウス ブラウン", "アクシーズファム 茶 ブラウス",
    "アクシーズファム レース ブラウス 茶色"
]

def load_seen_urls():
    try:
        if os.path.exists(SEEN_FILE):
            file_time = os.path.getmtime(SEEN_FILE)
            # Only reset cache if it's older than 24 hours
            if datetime.now().timestamp() - file_time > 86400:
                os.rename(SEEN_FILE, f"{SEEN_FILE}.bak")
                return set()
            
            # Load the existing cache
            with open(SEEN_FILE, 'r', encoding='utf-8') as f:
                urls = json.load(f)
                return set(urls)
        else:
            return set()
    except Exception as e:
        print(f"❌ Error loading cache: {e}")
        return set()

def save_seen_urls(seen):
    try:
        # Create a backup of the existing file if it exists
        if os.path.exists(SEEN_FILE):
            backup_file = f"{SEEN_FILE}.bak"
            try:
                os.replace(SEEN_FILE, backup_file)
            except:
                pass
        
        # Write the new cache
        with open(SEEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(seen), f)
    except Exception as e:
        print(f"❌ Error saving cache: {e}")

def get_driver():
    """Create a Chromium WebDriver with headless mode for maximum stability"""
    # Use Chrome options with headless mode
    options = ChromeOptions()
    
    # Always use the specific Chromium binary path
    chromium_path = "C:/chrome-win/chrome.exe"
    
    if os.path.exists(chromium_path):
        logging.info(f"Using Chromium binary at: {chromium_path}")
        options.binary_location = chromium_path
    else:
        logging.warning(f"Chromium not found at {chromium_path}, falling back to system Chrome")
    
    # Use proper headless mode with stability enhancements
    # For Chrome/Chromium 108+, we need to use --headless=new
    options.add_argument("--headless=new")  # More stable new headless implementation
    
    # Core stability options - expanded with more settings to prevent crashes
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1024")  # Larger window size helps stability
    
    # Headless-specific stability flags
    options.add_argument("--disable-dev-shm-usage")  # Critical for headless in containers
    options.add_argument("--remote-debugging-port=9222")  # Helps with stability
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--mute-audio")
    options.add_argument("--no-first-run")
    
    # Additional memory settings to improve stability
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-notifications")
    options.add_argument("--incognito")
    options.add_argument("--disable-popup-blocking")
    
    # Process isolation - critical for stability in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")
    
    # Memory settings to avoid tab crashes in headless mode
    options.add_argument("--disable-infobars")
    options.add_argument("--js-flags=--max_old_space_size=2048")  # Increase JS memory limit
    options.add_argument("--memory-pressure-off")  # Disable memory pressure handling
    options.add_argument("--deterministic-mode")   # More stable but slower
    
    # Experimental options to improve stability
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.images": 2,  # Don't load images
        "profile.default_content_setting_values.cookies": 1, # Accept cookies
        "profile.managed_default_content_settings.javascript": 1,  # Enable JavaScript
        "profile.managed_default_content_settings.plugins": 1,     # Enable plugins
    })
    
    # Only disable images if necessary - sometimes this can cause issues
    # options.add_argument("--blink-settings=imagesEnabled=false")
    
    # Add Chrome-specific stability settings
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Global driver reference
    global active_chrome_driver
    
    try:
        # Create the service with chromedriver path, add more logging
        service = ChromeService(CHROMEDRIVER_PATH)
        logging.info("Setting up Chrome with adjusted parameters for stability")
        
        # Initialize the driver with our options
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set very generous timeouts to prevent tab crashed errors
        driver.set_page_load_timeout(60)  # Increase to 60 seconds for slow connections
        driver.set_script_timeout(30)     # Increase to 30 seconds for slow script execution
        
        # Additional initialization to improve stability
        driver.implicitly_wait(10)        # Wait up to 10 seconds when looking for elements
        
        # Headless-specific initialization
        try:
            # Prime the browser with a simple operation 
            driver.get("about:blank")
            driver.execute_script("return navigator.userAgent")
            # Set window size explicitly again to ensure it took effect
            driver.set_window_size(1280, 1024)
        except:
            logging.warning("Initial browser priming failed, continuing anyway")
        
        # Store in global reference
        active_chrome_driver = driver
        logging.info("Successfully created Chrome driver with enhanced stability settings")
        return driver
    except Exception as e:
        logging.error(f"First Chrome driver attempt failed: {e}")
        
        try:
            # Try with automatic webdriver management
            logging.info("Trying Chrome driver with auto-discovery")
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(30)  # Increased from 20 to 30 seconds
            driver.set_script_timeout(20)     # Increased from 15 to 20 seconds
            
            # Store in global reference
            active_chrome_driver = driver
            logging.info("Successfully created Chrome driver with auto-discovery")
            return driver
        except Exception as e2:
            logging.error(f"All Chrome driver initialization attempts failed: {e}, {e2}")
            raise Exception("Failed to initialize Chrome WebDriver")

def send_to_discord(webhook_url, message, image_url=None):
    try:
        payload = {"content": message}
        if image_url:
            payload["embeds"] = [{"image": {"url": image_url}}]
        return requests.post(webhook_url, json=payload)
    except Exception as e:
        print(f"❌ Failed to send Discord message: {e}")
        return None

def translate_text(text):
    try:
        return GoogleTranslator(source='ja', target='en').translate(text)
    except Exception as e:
        return f"[Translation failed: {e}]"

def contains_brown_keyword(text):
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in BROWN_KEYWORDS)

def extract_usd_price(jpy):
    try:
        jpy_val = int(jpy.replace(",", ""))
        usd_val = round(jpy_val * 0.0069, 2)
        return f"≈ {usd_val} USD"
    except:
        return ""

def process_search_results(driver, soup, site, term, group, webhook_url, seen_urls, new_seen):
    """Process search results page for a specific term and site"""
    tiles = soup.find_all("div", class_="shop-item")
    processed_count = 0
    
    for tile in tiles:
        title_tag = tile.find("a", class_="inline-block w-full text-black truncate text-sm")
        price_tag = tile.find("span", class_="text-2xl font-bold")
        img_tag = tile.find("img")
        
        if not title_tag:
            continue
            
        relative_url = title_tag['href']
        full_url = f"https://www.fromjapan.co.jp{relative_url}"
        
        # Skip if URL has been seen before
        if full_url in seen_urls:
            continue
        
        # Process each item
        title = title_tag.get_text(strip=True)
        translated_title = translate_text(title)
        price = price_tag.get_text(strip=True) if price_tag else "N/A"
        usd_price = extract_usd_price(price)
        img_url = img_tag['src'] if img_tag else None
        
        # Get detailed page with proper resource management
        try:
            # Reset page state to clear memory
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            
            # Navigate to item page
            driver.get(full_url)
            
            # Shorter wait time to reduce hanging
            driver.implicitly_wait(5)
            time.sleep(1.5)  # Reduced from 2 seconds
            
            # Get iframe with more defensive approach
            try:
                # First attempt with standard wait
                iframe = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='googleTranslate.html']")))
                driver.switch_to.frame(iframe)
                
                # Get description with shorter timeout
                desc_element = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "leading-loose")))
                description = desc_element.text.strip()
                
                # Switch back to main context
                driver.switch_to.default_content()
            except Exception as iframe_error:
                # Fallback approach if the iframe method fails
                logging.warning(f"Iframe approach failed, trying direct description extraction: {iframe_error}")
                driver.switch_to.default_content()  # Ensure we're on the main page
                
                # Try multiple CSS selectors that might contain the description
                for selector in [".leading-loose", ".item-description", ".description", "p"]:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            description = "\n".join([el.text for el in elements if el.text.strip()])
                            if description:
                                break
                    except:
                        pass
                
                # If still no description, set a default
                if not description:
                    description = "[Description unavailable]"
            
            # Clear references to DOM elements 
            iframe = None
            desc_element = None
            
            # Clear JS memory
            driver.execute_script("window.history.go(0);")
            
            # Get translation
            translated_desc = translate_text(description)
        except Exception as e:
            logging.error(f"Error processing detail page for {full_url}: {str(e)[:100]}")
            description = "[No description found]"
            translated_desc = ""
            
            # Reset driver state on error
            try:
                driver.get("about:blank")
                driver.execute_script("window.localStorage.clear();")
            except:
                pass
        
        combined_text = f"{title}\n{description}"
        
        # Determine if the item should be sent
        filter_info = []
        
        # For no_filter webhooks, only send if the search term exactly matches what's specified
        if "nofilter" in group:
            # For these webhooks, only send results matching exactly their search terms
            should_send = True
            filter_info.append(f"Search: {term}")
        else:
            # Normal filtering for other search terms
            matches_brown = contains_brown_keyword(combined_text)
            matches_axes_extra = (
                group == "axesfemme" and any(kw in combined_text for kw in AXESFEMME_EXTRA_KEYWORDS))
            should_send = matches_brown or matches_axes_extra
            
            # Add filter info for display
            filter_info.append(f"Search: {term}")
            if matches_brown:
                filter_info.append("Filter: Brown")
            if matches_axes_extra:
                filter_info.append(f"Filter: Axes Femme Keywords ({', '.join([kw for kw in AXESFEMME_EXTRA_KEYWORDS if kw in combined_text])})")
        
        # If item matches criteria, send to webhook
        if should_send:
            # Join filter info for display
            filter_display = " | ".join(filter_info)
            
            message = (
                f"**🛒 {group.upper()} | {site.upper()} | {term}**\n"
                f"**Match:** {filter_display}\n"
                f"**Title (JP):** {title}\n"
                f"**Title (EN):** {translated_title}\n"
                f"**Price:** {price} JPY ({usd_price})\n"
                f"**Desc (JP):** {description[:200]}\n"
                f"**Desc (EN):** {translated_desc[:200]}\n"
                f"🔗 {full_url}")
            response = send_to_discord(webhook_url, message, image_url=img_url)
            
            if response and response.status_code in (200, 204):
                # Add to both current seen set and main seen set immediately
                new_seen.add(full_url)
                seen_urls.add(full_url)
                # Save cache after each successful send to prevent duplicates
                save_seen_urls(seen_urls)
                processed_count += 1
        
        # Force garbage collection after each item to prevent memory buildup
        if processed_count % 5 == 0 and processed_count > 0:
            gc.collect()
                
    return processed_count

def scrape_and_filter_items(driver):
    """Main function to scrape and filter items across all brands and sites
    
    Args:
        driver: The already initialized Firefox WebDriver instance
    """
    try:
        # Refresh the driver state before starting a new cycle
        try:
            driver.delete_all_cookies()
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            driver.execute_script("window.history.go(0);")
        except:
            # Ignore errors during cleanup
            pass
            
        seen_urls = load_seen_urls()
        new_seen = set()
        
        # 1. Create a list of all search combinations
        search_combinations = []
        for group, terms in SEARCH_TERMS.items():
            webhook_url = WEBHOOKS[group]
            for site, (base_url, sort_param) in BASE_URLS.items():
                for term in terms:
                    search_combinations.append({
                        'group': group,
                        'webhook_url': webhook_url,
                        'site': site,
                        'base_url': base_url,
                        'sort_param': sort_param,
                        'term': term
                    })
        
        # 2. Interleave brands by alternating between them
        interleaved_combinations = []
        brand_combinations = {}
        
        # Group search combinations by brand
        for combo in search_combinations:
            group = combo['group']
            if group not in brand_combinations:
                brand_combinations[group] = []
            brand_combinations[group].append(combo)
        
        # Create interleaved list by taking one from each brand at a time
        max_combos = max(len(combos) for combos in brand_combinations.values())
        for i in range(max_combos):
            for group, combos in brand_combinations.items():
                if i < len(combos):
                    interleaved_combinations.append(combos[i])
        
        # 3. Process each search combination in interleaved order
        total_processed = 0
        brand_stats = {group: 0 for group in SEARCH_TERMS.keys()}
        
        # More frequent driver refreshes to prevent tab crashes
        search_counter = 0
        driver_refresh_interval = 2  # Refresh driver every 2 searches to avoid memory issues
        
        for search in interleaved_combinations:
            # Recreate driver periodically to prevent memory leaks
            search_counter += 1
            if search_counter % driver_refresh_interval == 0:
                logging.info("Performing scheduled driver refresh")
                try:
                    # Get the old driver's cookies if needed
                    cookies = driver.get_cookies()
                    
                    # Quit the old driver properly
                    driver.quit()
                    active_chrome_driver = None
                    
                    # Force garbage collection
                    gc.collect()
                    
                    # Create a new driver
                    driver = get_driver()
                    # global reference is set in get_driver()
                    
                    # Restore cookies if needed
                    for cookie in cookies:
                        try:
                            driver.add_cookie(cookie)
                        except:
                            pass
                except Exception as refresh_error:
                    logging.error(f"Error during driver refresh: {refresh_error}")
                    # Continue with existing driver if refresh fails
            
            group = search['group']
            webhook_url = search['webhook_url']
            site = search['site']
            base_url = search['base_url']
            sort_param = search['sort_param']
            term = search['term']
            
            encoded_term = urllib.parse.quote(term)
            search_url = f"{base_url}{encoded_term}/-/{sort_param}"
            
            try:
                # Navigation with extensive error handling
                for nav_attempt in range(5):  # Try up to 5 times to load the page (increased from 3)
                    try:
                        logging.info(f"Navigating to {search_url} (attempt {nav_attempt+1})")
                        
                        # First clear the browser state
                        if nav_attempt > 0:
                            # Only do this on retry attempts
                            try:
                                driver.get("about:blank")
                                driver.delete_all_cookies()
                                driver.execute_script("window.localStorage.clear();")
                                driver.execute_script("window.sessionStorage.clear();")
                                time.sleep(1)  # Brief pause between reset and new request
                            except:
                                pass
                        
                        # Use JavaScript to navigate - sometimes more reliable than driver.get()
                        try:
                            driver.execute_script(f"window.location.href = '{search_url}';")
                            time.sleep(3)  # Give it time to start loading
                        except:
                            # Fall back to regular get method if JS fails
                            driver.get(search_url)
                        
                        # Wait with improved loading strategy
                        try:
                            # Give more time for the main page to load (15 seconds)
                            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "shop-item")))
                            logging.info("Found shop items successfully")
                            break  # Success - exit the retry loop
                        except Exception as wait_err1:
                            # Try with more generous fallback strategy
                            try:
                                # Wait for basic page structure
                                if nav_attempt < 2:  # Not last attempt yet
                                    logging.info("Waiting longer for page to load...")
                                    time.sleep(5)  # Wait 5 seconds
                                    
                                    # Check for any significant content after waiting
                                    if len(driver.page_source) > 5000:
                                        logging.info("Page has loaded with content after waiting")
                                        break
                                    else:
                                        # Try a reload if still not enough content
                                        driver.refresh()
                                        time.sleep(3)
                                        logging.info("Page refreshed, checking again")
                                        
                                        # Final check after refresh
                                        if len(driver.page_source) > 5000:
                                            logging.info("Page has content after refresh")
                                            break
                                        else:
                                            raise Exception("Page still missing content after refresh")
                                else:
                                    # On the last attempt, proceed anyway
                                    logging.info("Final attempt - proceeding with available content")
                                    break
                            except Exception as wait_err2:
                                if nav_attempt < 2:  # Only log and retry if not on last attempt
                                    logging.warning(f"Navigation attempt {nav_attempt+1} failed: {wait_err2}")
                                    # Reset the browser state before retry
                                    driver.get("about:blank")
                                    time.sleep(1)
                                else:
                                    # On last attempt, proceed with whatever we have
                                    logging.warning("All navigation attempts struggled, using current state")
                                    break
                    except Exception as nav_err:
                        if nav_attempt < 2:  # Only retry if not on last attempt
                            logging.warning(f"Navigation error on attempt {nav_attempt+1}: {nav_err}")
                            # Reset the browser state before retry
                            try:
                                driver.get("about:blank")
                                time.sleep(1)
                            except:
                                pass
                        else:
                            logging.error(f"All navigation attempts failed for {search_url}")
                            raise  # Re-raise on final attempt
                
                # Ultra-safe BeautifulSoup parsing
                try:
                    # Get page source with error handling
                    try:
                        page_source = driver.page_source
                    except Exception as page_err:
                        logging.error(f"Error getting page source: {page_err}")
                        page_source = "<html><body></body></html>"
                    
                    # Create soup with minimal parser and error handling
                    soup = BeautifulSoup(page_source, 'html.parser', parse_only=None, from_encoding="utf-8")
                    
                    # Clear page source reference from both python and browser memory
                    page_source = None
                    try:
                        driver.execute_script("document.body.innerHTML = '';")
                    except:
                        pass
                    
                except Exception as soup_error:
                    logging.error(f"BeautifulSoup creation failed: {soup_error}")
                    # Create empty soup as fallback
                    soup = BeautifulSoup("<html><body></body></html>", 'html.parser')
                
                # Process results with error handling
                try:
                    processed = process_search_results(
                        driver, soup, site, term, group, webhook_url, seen_urls, new_seen
                    )
                except Exception as process_err:
                    logging.error(f"Process error for {search_url}: {process_err}")
                    processed = 0
                total_processed += processed
                brand_stats[group] += processed
                
                # Clean up BeautifulSoup object to release memory
                soup.decompose()
                soup = None
                
                # Run garbage collection after processing to free memory
                gc.collect()
                gc.collect()
                
            except Exception as e:
                logging.error(f"Error processing search {term} on {site}: {e}")
                # Navigate to blank page to release resources
                try:
                    driver.get("about:blank")
                    # Additional cleanup for Edge browser
                    driver.execute_script("window.localStorage.clear();")
                    driver.execute_script("window.sessionStorage.clear();")
                    # Try to reset browser state without crashing
                    driver.execute_script("window.history.go(0);")
                except:
                    # If we can't clean up the driver, let's recreate it
                    try:
                        logging.warning("Driver appears unstable, recreating after search error")
                        driver.quit()
                        gc.collect(2)
                        driver = get_driver()
                    except:
                        pass
        
        return total_processed
        
    except Exception as e:
        print(f"❌ Error in scrape_and_filter_items: {e}")
        # We don't close the driver here anymore - we just reset it
        try:
            # Attempt to reset driver to a clean state
            driver.get("about:blank")
            driver.delete_all_cookies()
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
        except:
            # Ignore errors during cleanup
            pass
        
        # Re-raise the exception for the main error handler
        raise

# Global variable to store active Chrome driver
active_chrome_driver = None

def terminate_all_chrome_processes():
    """Force kill all Chrome/Chromium processes that might have been started by this script"""
    try:
        logging.info("Terminating all Chrome/Chromium browser processes")
        if sys.platform.startswith('win'):
            # On Windows, use taskkill to force terminate Chrome/Chromium processes
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            # Specifically terminate Chromium if it's running
            subprocess.run(['taskkill', '/F', '/IM', 'chromium.exe'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
                           
            # Kill any potential Chromium processes from the custom installation
            try:
                # This tries to find and kill all chrome.exe processes associated with C:\chrome-win
                result = subprocess.run(['wmic', 'process', 'where', 'ExecutablePath like "%C:\\\\chrome-win\\\\chrome.exe%"', 'delete'],
                              stdout=subprocess.DEVNULL, 
                              stderr=subprocess.DEVNULL)
            except:
                pass
            # Also kill any chromedriver processes
            subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
        elif sys.platform.startswith('linux'):
            # On Linux/WSL, use pkill to terminate Chrome/Chromium processes
            subprocess.run(['pkill', '-f', 'chrome'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'chromium'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
        
        logging.info("All Chrome processes terminated")
    except Exception as e:
        logging.error(f"Error terminating Chrome processes: {e}")

def cleanup_on_exit():
    """Cleanup function that runs when the script exits for any reason"""
    global active_chrome_driver
    try:
        logging.info("Application exit detected, performing cleanup")
        
        # First try to properly quit any active driver
        if active_chrome_driver:
            try:
                active_chrome_driver.quit()
                logging.info("WebDriver closed gracefully")
            except:
                pass
            active_chrome_driver = None
            
        # Force terminate any remaining Chrome processes to ensure clean exit
        terminate_all_chrome_processes()
        
        logging.info("Cleanup completed successfully")
    except Exception as e:
        logging.error(f"Error during exit cleanup: {e}")

# Register cleanup handlers for proper termination
atexit.register(cleanup_on_exit)

# Register signal handlers for proper termination on SIGTERM/SIGINT
def signal_handler(sig, frame):
    logging.info(f"Received signal {sig}, initiating shutdown")
    cleanup_on_exit()
    sys.exit(0)

# Register signal handlers if on Unix-like systems
if not sys.platform.startswith('win'):
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def clean_system_resources(driver=None):
    """Clean up system resources to prevent memory leaks and disk space issues
    
    Args:
        driver: Optional WebDriver instance to perform additional cleanup on
    """
    try:
        # Remove chromedriver log files
        for log_file in glob.glob('chromedriver*.log'):
            try:
                os.remove(log_file)
            except:
                pass
        
        # Reset browser state if driver is provided
        if driver:
            try:
                # Clear browser state without closing the browser
                driver.execute_script("window.localStorage.clear();")
                driver.execute_script("window.sessionStorage.clear();")
                driver.execute_script("window.history.replaceState(null, '', 'about:blank');")
                driver.delete_all_cookies()
                # Navigate to a blank page to free memory from previous pages
                driver.get("about:blank")
                # Clear any page content to free memory
                driver.execute_script("document.body.innerHTML = '';")
            except:
                pass  # Ignore errors during driver cleanup
        
        # Force Python garbage collection - more aggressive with generational cleanup
        gc.collect(2)  # Full collection including oldest generation
        
        # Log memory usage if psutil is available
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss / 1024 / 1024  # In MB
            logging.info(f"Memory usage: {memory_usage:.2f} MB")
            
            # Try to reduce memory usage if it's getting too high
            if memory_usage > 500:  # If using more than 500MB
                logging.warning(f"High memory usage detected: {memory_usage:.2f} MB, attempting cleanup")
                # More aggressive memory cleanup
                gc.collect(2)
                
                # Windows-specific memory optimization
                if hasattr(process, "memory_maps") and sys.platform.startswith('win'):
                    try:
                        # Call Windows working set trim API via ctypes
                        import ctypes
                        ctypes.windll.psapi.EmptyWorkingSet(process.pid)
                        logging.info("Trimmed Windows working set to reduce memory usage")
                    except:
                        pass
        except ImportError:
            pass
    except Exception as e:
        logging.error(f"Error cleaning resources: {e}")
        pass

if __name__ == "__main__":
    # Check if Chrome driver exists
    if not os.path.exists(CHROMEDRIVER_PATH):
        error_msg = f"Chrome WebDriver not found at {CHROMEDRIVER_PATH}. Please download from https://chromedriver.chromium.org/downloads"
        logging.error(error_msg)
        print(f"❌ ERROR: {error_msg}")
        print("You need to install Chrome/Chromium and the matching ChromeDriver version.")
        sys.exit(1)
    
    # First, kill any existing Chrome and ChromeDriver processes
    if sys.platform.startswith('win'):
        try:
            logging.info("Terminating any existing browser processes...")
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            time.sleep(1)  # Give time for processes to terminate
        except:
            pass
    
    # Skip regular Chrome validation, directly try to use Chromium
    chromium_path = "C:/chrome-win/chrome.exe"
    
    if os.path.exists(chromium_path):
        logging.info(f"Found Chromium at {chromium_path}, using it directly...")
        
        try:
            # Create options specifically for Chromium with improved stability
            options = ChromeOptions()
            options.binary_location = chromium_path
            
            # Use proper headless mode for validation
            options.add_argument("--headless=new")  # Newer headless implementation is more stable
            
            # Essential stability options
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1280,1024")
            options.add_argument("--disable-features=NetworkService")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
            
            # Create direct service with ChromeDriver
            service = ChromeService(CHROMEDRIVER_PATH)
            
            # Test with explicit binary and service
            test_driver = webdriver.Chrome(service=service, options=options)
            version = test_driver.capabilities.get('browserVersion', 'unknown')
            logging.info(f"Chromium validation successful - Version: {version}")
            test_driver.quit()
        except Exception as e:
            logging.error(f"Chromium validation failed: {e}")
            print(f"❌ WARNING: Chromium validation failed with binary at {chromium_path}")
            print(f"Error: {str(e)[:200]}")
            print("Please ensure ChromeDriver version matches your Chromium version exactly")
            print(f"Check version with: {chromium_path} --version")
    else:
        logging.warning(f"Chromium not found at {chromium_path}, trying with system Chrome...")
        # Fall back to regular Chrome with minimal validation
        try:
            options = ChromeOptions()
            # Use proper headless mode for system Chrome
            options.add_argument("--headless=new")
            
            # Add essential stability options for system Chrome
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-features=NetworkService")
            
            test_driver = webdriver.Chrome(options=options)
            version = test_driver.capabilities.get('browserVersion', 'unknown')
            logging.info(f"System Chrome validation successful - Version: {version}")
            test_driver.quit()
        except Exception as e:
            logging.error(f"All browser validation failed: {e}")
            print(f"❌ WARNING: All browser validation failed: {str(e)[:200]}")
            print("The script will try to run, but you may encounter errors")
    
    # Check if Chromium was successfully validated
    if os.path.exists("C:/chrome-win/chrome.exe"):
        browser_type = "Chromium"
    else:
        browser_type = "Chrome"
    
    for name, url in WEBHOOKS.items():
        send_to_discord(url, f"✅ FromJapan Brown Item Monitor for **{name.upper()}** has started ({browser_type} version) and is running in the background.")
    
    # Track errors for exponential backoff
    consecutive_errors = 0
    
    # Create a single Edge instance that will be reused throughout the script's lifecycle
    driver = None
    
    # Track driver uptime to perform periodic full restarts
    driver_creation_time = None
    max_driver_uptime = 3600 * 4  # Fully recreate driver every 4 hours to prevent memory leaks
    
    try:
        # Initialize the WebDriver once at startup
        logging.info("Initializing Chrome WebDriver...")
        driver = get_driver()
        driver_creation_time = time.time()
        
        # Get and log Chrome browser version for troubleshooting
        try:
            chrome_version = driver.capabilities.get('browserVersion', 'unknown')
            browser_name = driver.capabilities.get('browserName', 'unknown')
            logging.info(f"Using {browser_name} version {chrome_version}")
            
            # Also log driver capabilities for debugging
            logging.info(f"Driver capabilities: {driver.capabilities}")
        except Exception as cap_error:
            logging.warning(f"Unable to get browser version: {cap_error}")
        
        while True:
            try:
                # Check if we need to completely recreate the driver based on uptime
                current_time = time.time()
                if driver_creation_time and (current_time - driver_creation_time > max_driver_uptime):
                    logging.info(f"Driver has been running for {(current_time - driver_creation_time) // 60} minutes - performing scheduled full restart")
                    try:
                        if driver:
                            driver.quit()
                    except:
                        pass
                    
                    # Force Python to clean up memory before creating a new driver
                    gc.collect(2)
                    
                    # Create a new driver
                    driver = get_driver()
                    driver_creation_time = time.time()
                    logging.info("Driver fully restarted to prevent memory leaks")
                
                # Clean up system resources before each cycle (with the driver instance)
                clean_system_resources(driver)
                
                # Run the main scraping function with our persistent driver
                scrape_and_filter_items(driver)
                
                # If successful, reset error counter
                consecutive_errors = 0
                
                # Log success
                logging.info("Completed search cycle successfully")
                
                # Force garbage collection between cycles
                gc.collect(2)
                
                # Standard wait between cycles
                time.sleep(600)
                
            except Exception as e:
                # Implement exponential backoff for error recovery
                consecutive_errors += 1
                
                # Calculate backoff time (max 2 hours)
                backoff_time = min(600 * (2 ** consecutive_errors), 7200)
                
                # Log the error
                error_msg = f"❌ Script encountered an error and will retry in {backoff_time//60} minutes: {str(e)[:500]}"
                print(error_msg)
                logging.error(error_msg)
                
                # Only notify on Discord after multiple consecutive errors
                if consecutive_errors >= 3:
                    for url in WEBHOOKS.values():
                        send_to_discord(url, error_msg)
                
                # Check if driver is still responding, recreate if needed
                try:
                    # Simple check to see if driver is still responding
                    driver.current_url
                except:
                    # Driver seems crashed, recreate it
                    try:
                        logging.warning("WebDriver appears to be crashed, recreating...")
                        if driver:
                            try:
                                driver.quit()
                            except:
                                pass
                        
                        # Force kill any Chrome processes left behind
                        terminate_all_chrome_processes()
                        active_chrome_driver = None
                        
                        # Wait a moment for processes to fully terminate
                        time.sleep(2)
                        
                        # Create a new driver
                        driver = get_driver()
                        driver_creation_time = time.time()
                        logging.info("WebDriver recreated successfully")
                    except Exception as driver_error:
                        logging.error(f"Failed to recreate WebDriver: {driver_error}")
                
                # Force GC after errors
                gc.collect(2)
                
                time.sleep(backoff_time)
    
    # Always properly clean up the driver at script exit
    finally:
        if driver:
            try:
                driver.quit()
                logging.info("WebDriver closed successfully")
            except:
                pass
        
        # Final cleanup - ensure all Chrome processes are terminated
        terminate_all_chrome_processes()
        active_chrome_driver = None
        logging.info("Final cleanup completed - all Chrome browser instances terminated")