import csv
import time
import requests

def check_urls():
    input_file = '/Users/codingmart/test/live-page-status/url.csv'
    output_file = '/Users/codingmart/test/live-page-status/404.csv'
    
    # Try to open the input file
    try:
        with open(input_file, mode='r', newline='', encoding='utf-8') as f:
            # We assume URLs are in the first column
            reader = csv.reader(f)
            urls = []
            for row in reader:
                if row and row[0].strip():
                    urls.append(row[0].strip())
    except FileNotFoundError:
        print(f"Input file {input_file} not found.")
        return

    if not urls:
        print("No URLs found to process.")
        return

    # Prepare to write to the output file
    with open(output_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['URL', 'Status Code']) # Write header
        
        count = 0
        for url in urls:
            count += 1
            
            # Make the HTTP request
            try:
                # Add a timeout and a generic User-Agent
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                
                # Add http:// if scheme is missing
                if not url.startswith(('http://', 'https://')):
                    url = 'http://' + url
                    
                response = requests.get(url, headers=headers, timeout=15)
                
                print(f"[{count}] Checked {url} - Status: {response.status_code}")
                
                # If 404, write to 404.csv
                if response.status_code == 404:
                    writer.writerow([url, response.status_code])
                    f.flush() # Ensure data is written immediately
            except requests.RequestException as e:
                print(f"[{count}] Error checking {url}: {e}")
                
            # After every 5 URLs, take a 6-second break (unless it's the last URL)
            if count % 5 == 0 and count < len(urls):
                print("Processed 5 URLs. Taking a 6-second break...")
                time.sleep(5)

if __name__ == '__main__':
    check_urls()
