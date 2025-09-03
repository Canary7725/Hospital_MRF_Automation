import glob
import os
import time
import json
import random
import pandas as pd
from urllib.parse import urljoin, urlparse
from selenium_utils import SeleniumHandler
from get_source_and_mrf_cms_txt import get_best_mrf_match_selenium


def load_config():
    with open('./config.json') as config:
        return json.load(config)


def main():
    start_time = time.time()
    selenium = SeleniumHandler(headless=True)

    config = load_config()
    df = pd.read_csv("test.csv")
    # df=pd.read_excel(config['filename'],sheet_name=config['sheetname'], usecols=['Facility ID','Facility Name','City/Town','State'])
    # df=df[df['State']==config['state']]
    df['Hospital Link'] = ''
    df['has_cms_txt'] = False
    df['Source URL'] = ''
    df['File URL'] = ''

    # Create screenshots directory if it doesn't exist
    os.makedirs("screenshots", exist_ok=True)

    driver_restart_counter = 0
    max_driver_restarts = 10

    for i, row in df.iterrows():
        try:
            search_query = f"{row['Facility Name']} {row['City/Town']}"
            print(f"[{i+1}/{len(df)}] Searching: {search_query}")
            
            result_url = selenium.get_url(search_query)

            if result_url:
                parsed = urlparse(result_url)
                root_url = f"{parsed.scheme}://{parsed.netloc}"
                cms_url = urljoin(root_url, "cms-hpt.txt")
                
                # Try to get MRF match from CMS file (includes URL existence check)
                result_links = get_best_mrf_match_selenium(selenium, cms_url, search_query)
                
                if result_links is not False and result_links:  # CMS file exists and has matches
                    df.at[i, 'Hospital Link'] = cms_url
                    df.at[i, 'has_cms_txt'] = True
                    print(f"Found CMS: {cms_url}")
                    for source, mrf in result_links:
                        df.at[i, 'Source URL'] = source
                        df.at[i, 'File URL'] = mrf
                elif result_links is not False:  # CMS file exists but no matches
                    df.at[i, 'Hospital Link'] = cms_url
                    df.at[i, 'has_cms_txt'] = True
                    print(f"Found CMS but no matching records: {cms_url}")
                else:  # CMS file doesn't exist
                    df.at[i, 'Hospital Link'] = root_url
                    df.at[i, 'has_cms_txt'] = False
                    # Try manual search for source and MRF
                    source, mrf = selenium.get_source_mrf_manually(root_url, search_query)
                    df.at[i, 'Source URL'] = source
                    df.at[i, 'File URL'] = mrf

            else:
                df.at[i, 'Hospital Link'] = "Link Not Found"
                print("No valid link found.")

            # Save progress after each row
            if (i + 1) % 5 == 0:  # Save every 5 rows
                df.to_csv("output_links_progress.csv", index=False)
                print(f"Progress saved after {i + 1} rows")

            # Restart driver periodically to prevent memory issues
            if (i + 1) % 10 == 0:
                print(f"Restarting driver after {i + 1} rows for maintenance...")
                selenium.restart_driver()
                driver_restart_counter += 1
                
                # If we've restarted too many times, there might be a persistent issue
                if driver_restart_counter >= max_driver_restarts:
                    print("Too many driver restarts. There might be a persistent issue.")
                    break

            time.sleep(random.uniform(4, 9))
            
        except Exception as e:
            print(f"Error processing row {i+1}: {e}")
            df.at[i, 'Hospital Link'] = f"Error: {str(e)}"
            
            # If it's a driver-related error, restart the driver
            if any(keyword in str(e).lower() for keyword in ['timeout', 'connection', 'webdriver', 'chrome']):
                print("Driver-related error detected. Restarting driver...")
                selenium.restart_driver()
                driver_restart_counter += 1
            
            continue

    selenium.close()
    df.to_csv("output_links.csv", index=True)

    print("Done. Results saved to output_links.csv")
    print(f"Execution Time: {time.time() - start_time:.2f} seconds")
    print(f"Driver was restarted {driver_restart_counter} times")


if __name__ == "__main__":
    main()