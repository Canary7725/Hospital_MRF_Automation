import time
import re
import pandas as pd
from selenium_utils import SeleniumHandler
from selenium.webdriver.common.by import By

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)  # Remove punctuation
    return set(text.split())

def get_best_mrf_match_selenium(selenium_handler, url, hospital_name, min_overlap=2):
    """
    Finds the best (source-page-url, mrf-url) match from a CMS .txt file based on keyword overlap.
    Uses Selenium instead of requests to avoid 403 errors.
    First checks if the URL exists, returns False if not found.
    """
    # First check if the CMS URL exists
    if not selenium_handler.url_exists_selenium(url):
        print(f"CMS URL not found: {url}")
        return False
    
    try:
        # Use Selenium to get the content instead of requests
        selenium_handler.driver.get(url)
        time.sleep(3)  # Give page time to load
        selenium_handler.wait_for_page_load()
        
        # Get the page source (text content)
        page_source = selenium_handler.driver.page_source
        
        try:
            if '<pre>' in page_source or page_source.count('<') < 10:  # Likely a plain text file
                # Extract text from <pre> tags or get all text
                text_content = selenium_handler.driver.find_element(By.TAG_NAME, 'body').text
            else:
                text_content = page_source
        except:
            text_content = page_source
        
        lines = text_content.splitlines()        
    except Exception as e:
        print(f"Error fetching file from {url}: {e}")
        return False

    hospital_words = normalize(hospital_name)
    best_match = None
    max_overlap = 0
    record = {}

    for line in lines + [""]:  # Forces last record to be processed
        line = line.strip()
        if line.lower().startswith("location-name:") and record:
            location = record.get("location-name", "")
            location_words = normalize(location)
            overlap = len(location_words & hospital_words)
            if overlap >= min_overlap and overlap > max_overlap:
                max_overlap = overlap
                best_match = (record.get("source-page-url", ""), record.get("mrf-url", ""))
            record = {}

        if not line:
            if record:
                location = record.get("location-name", "")
                location_words = normalize(location)
                overlap = len(location_words & hospital_words)
                if overlap >= min_overlap and overlap > max_overlap:
                    max_overlap = overlap
                    best_match = (record.get("source-page-url", ""), record.get("mrf-url", ""))
            record = {}
        else:
            if ":" in line:
                key, value = line.split(":", 1)
                record[key.strip().lower()] = value.strip()


    return [best_match] if best_match else []

def get_best_mrf_match(url, hospital_name, min_overlap=2):
    """
    Wrapper function that creates a Selenium instance for fetching CMS text files
    """
    selenium_handler = SeleniumHandler(headless=False)
    try:
        result = get_best_mrf_match_selenium(selenium_handler, url, hospital_name, min_overlap)
        return result
    finally:
        selenium_handler.close()

def main():
    start_time = time.time()
    df = pd.read_csv('output_links.csv')
    df['source_link'] = ''
    df['mrf_link'] = ''
    df['source_link'] = df['source_link'].astype('object')
    df['mrf_link'] = df['mrf_link'].astype('object')

    # Create a single Selenium instance for all operations to improve performance
    selenium_handler = SeleniumHandler(headless=False)
    
    try:
        for i, row in df.iterrows():
            url = row['hospital_link']
            if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
                continue  # skip invalid URLs

            search_query = f"{row['Facility Name']} {row['City/Town']}"
            result = get_best_mrf_match_selenium(selenium_handler, url, search_query)

            if result:
                df.at[i, 'source_link'], df.at[i, 'mrf_link'] = result[0]
                
            time.sleep(2)
    finally:
        selenium_handler.close()

    df.to_csv('test_cms_output.csv', index=False)
    print(df)

    end_time = time.time()
    result_time = end_time - start_time
    print(f"Execution time: {result_time:.2f} seconds")


if __name__ == '__main__':
    main()