import csv
import urllib.request
import urllib.error
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

input_file = '/Users/codingmart/test/page-status/url.csv'
output_file = '/Users/codingmart/test/page-status/page-report-404.csv'

# Create a permissive SSL context in case of certificate issues
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

file_lock = threading.Lock()

def check_url(url, writer, outfile):
    if not url:
        return {'url': url, 'status': 'EMPTY'}
    
    # Ensure the URL has a scheme
    original_url = url
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'http://' + url

    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0'}
    )

    try:
        urllib.request.urlopen(req, context=ctx, timeout=10)
        return {'url': original_url, 'status': '200 OK'}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            with file_lock:
                writer.writerow([original_url])
                outfile.flush()
            return {'url': original_url, 'status': '404 Not Found'}
        else:
            return {'url': original_url, 'status': f'{e.code} Error'}
    except Exception as e:
        return {'url': original_url, 'status': f'Error: {type(e).__name__}'}

def check_pages():
    urls = []
    with open(input_file, mode='r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        for row in reader:
            if row and row[0].strip():
                urls.append(row[0].strip())

    with open(output_file, mode='w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(['url'])
        outfile.flush()

        print(f"Checking {len(urls)} URLs concurrently...")
        
        # Use 20 threads to speed up the process
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_url = {executor.submit(check_url, url, writer, outfile): url for url in urls}
            
            count = 0
            for future in as_completed(future_to_url):
                count += 1
                try:
                    res = future.result()
                    if res:
                        print(f"[{count}/{len(urls)}] {res['url']} -> {res['status']}")
                except Exception as exc:
                    url = future_to_url[future]
                    print(f"[{count}/{len(urls)}] {url} generated an exception: {exc}")

if __name__ == '__main__':
    check_pages()
    print(f"\nDone. 404 URLs are saved to {output_file}")
