import os
import time
import json
import random
import pandas as pd
from urllib.parse import urljoin, urlparse
from selenium_utils import SeleniumHandler, url_exists
from get_source_and_mrf_cms_txt import get_best_mrf_match


def load_config():
    with open('./config.json') as config:
        return json.load(config)


def main():
    start_time = time.time()
    selenium = SeleniumHandler(headless=True)

    config = load_config()
    # df = pd.read_csv("test.csv")
    df=pd.read_excel(config['filename'],sheet_name=config['sheetname'], usecols=['Facility Id','Facility Name','City/Town','State'])
    print(df.head(10))
    df['Hospital Link'] = ''
    df['has_cms_txt'] = False
    df['Source URL'] = ''
    df['File URL'] = ''

    for i, row in df.iterrows():
        search_query = f"{row['Facility Name']} {row['City/Town']}"
        print(f"[{i+1}/{len(df)}] Searching: {search_query}")
        result_url = selenium.get_url(search_query)

        if result_url:
            parsed = urlparse(result_url)
            root_url = f"{parsed.scheme}://{parsed.netloc}"
            cms_url = urljoin(root_url, "cms-hpt.txt")
            
            if url_exists(cms_url):
                df.at[i, 'Hospital Link'] = cms_url
                df.at[i, 'has_cms_txt'] = True
                print(f"Found CMS: {cms_url}")
                result_links=get_best_mrf_match(cms_url,search_query)
                for source,mrf in result_links:
                    df.at[i,'Source URL']=source
                    df.at[i,'File URL']=mrf
            else:
                source,mrf=selenium.get_soruce_mrf_manually(root_url,search_query)
                df.at[i, 'Hospital Link'] = root_url
                df.at[i,'Source URL']=source
                df.at[i,'File URL']=mrf

        else:
            df.at[i,'Hospital Link'] = "Link Not Found"
            print("No valid link found.")

        time.sleep(random.uniform(4, 9))

    selenium.close()
    df.to_csv("output_links.csv", index=False)

    print("Done. Results saved to output_links.csv")
    print(f"Execution Time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
