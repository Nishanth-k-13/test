import csv
import requests
from bs4 import BeautifulSoup
import concurrent.futures
from urllib3.exceptions import InsecureRequestWarning
import warnings

warnings.simplefilter('ignore', InsecureRequestWarning)

CSV_FILE = '/Users/codingmart/test/key-ratios/url.csv'
OUTPUT_FILE = '/Users/codingmart/test/key-ratios/live-stats-report.csv'
NO_DATA_FILE = '/Users/codingmart/test/key-ratios/no-data-url.csv'

def check_url(url):
    result = {
        'url': url,
        'has_section': False,
        'has_data': False,
        'error': None
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # The Card wrapper for Share Price Live Stats has id="share-price-live-stats"
        section = soup.find(id='share-price-live-stats')
        if section:
            result['has_section'] = True
            
            # If there is data, this div will exist
            content = soup.find(id='share-price-live-stats-content')
            if content:
                result['has_data'] = True
                
    except Exception as e:
        result['error'] = str(e)
        
    return result

def main():
    urls = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    urls.append(row[0].strip())
    except FileNotFoundError:
        print(f"Error: Could not find {CSV_FILE}")
        return

    print(f"Loaded {len(urls)} URLs. Starting checks...")

    results = []
    # Using ThreadPoolExecutor to speed up fetching URLs
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # submit all tasks
        future_to_url = {executor.submit(check_url, url): url for url in urls}
        
        count = 0
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            count += 1
            try:
                res = future.result()
                results.append(res)
                
                # Simple status string for progress logging
                if res['error']:
                    status = f"ERROR: {res['error']}"
                elif res['has_data']:
                    status = "OK (Has Data)"
                elif res['has_section']:
                    status = "NO DATA (Section Present)"
                else:
                    status = "NO SECTION"
                    
                print(f"[{count}/{len(urls)}] {url} -> {status}")
            except Exception as exc:
                print(f"[{count}/{len(urls)}] {url} generated an exception: {exc}")

    # Write results to CSV
    keys = ['url', 'has_section', 'has_data', 'error']
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
        
    print(f"\nDone. Report saved to {OUTPUT_FILE}")

    # Write no-data-urls to CSV
    no_data_urls = [r['url'] for r in results if not r['has_data']]
    with open(NO_DATA_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['url'])
        for u in no_data_urls:
            writer.writerow([u])
    print(f"Saved {len(no_data_urls)} URLs with no data to {NO_DATA_FILE}")
    # Print summary
    total = len(results)
    with_data = sum(1 for r in results if r['has_data'])
    without_data = sum(1 for r in results if r['has_section'] and not r['has_data'])
    errors = sum(1 for r in results if r['error'])
    
    print(f"\n--- Summary ---")
    print(f"Total URLs Checked: {total}")
    print(f"With Data: {with_data}")
    print(f"Without Data (Section Present): {without_data}")
    print(f"Errors: {errors}")

if __name__ == '__main__':
    main()
