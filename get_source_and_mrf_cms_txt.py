import time
import requests
import re
import pandas as pd

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)  # Remove punctuation
    return set(text.split())

def get_best_mrf_match(url, hospital_name, min_overlap=2):
    """
    Finds the best (source-page-url, mrf-url) match from a CMS .txt file based on keyword overlap.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.5735.110 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
    except requests.RequestException as e:
        print(f"Error fetching file from {url}: {e}")
        return []

    hospital_words = normalize(hospital_name)
    best_match = None
    max_overlap = 0
    record = {}

    for line in lines + [""]:  # Ensures final record is processed
        line = line.strip()
        if not line:
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
                record[key.strip()] = value.strip()

    return [best_match] if best_match else []

def main():
    start_time=time.time()
    df = pd.read_csv('cms_txt.csv')
    df['source_link'] = ''
    df['mrf_link'] = ''
    df['source_link'] = df['source_link'].astype('object')
    df['mrf_link'] = df['mrf_link'].astype('object')

    for i, row in df.iterrows():
        url = row['hospital_link']
        if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
            continue  # skip invalid URLs

        search_query = f"{row['Facility Name']} {row['City/Town']}"
        result = get_best_mrf_match(url, search_query)

        if result:
            df.at[i, 'source_link'], df.at[i, 'mrf_link'] = result[0]

    df.to_csv('test_cms_output.csv', index=False)
    print(df)

    end_time=time.time()
    result_time=end_time-start_time
    print(f"Execution time: {result_time:.2f} seconds")


if __name__=='__main__':
    main()
