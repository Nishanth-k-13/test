import csv
import time
import random
import requests
import concurrent.futures
import os

# Path to the URLs CSV file in the parent directory
URLS_FILE = os.path.join(os.path.dirname(__file__), '..', 'urls.csv')
urls = []

try:
    with open(URLS_FILE, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].strip():
                urls.append(row[0].strip())
except FileNotFoundError:
    print(f"Error: Could not find {URLS_FILE}")
    urls = []

def fetch_url(url):
    """Fetches a single URL and returns status code and response time."""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=15)
        elapsed = time.time() - start_time
        return url, response.status_code, elapsed
    except Exception as e:
        return url, str(e), 0

def run_load_test(concurrency=10, duration_seconds=60):
    """Runs a basic load test against the URLs for a specific duration."""
    if not urls:
        print("No URLs to test. Please ensure urls.csv exists and is populated.")
        return

    print(f"Starting load test...")
    print(f"Concurrency: {concurrency} workers")
    print(f"Duration: {duration_seconds} seconds")
    print("-" * 40)
    
    results = []
    start_time = time.time()
    
    # Use ThreadPoolExecutor for concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        # Keep track of running futures
        futures = set()
        
        # Helper function to submit a new random URL request
        def submit_new_request():
            url = random.choice(urls)
            return executor.submit(fetch_url, url)
        
        # Initial batch of requests up to concurrency limit
        for _ in range(concurrency):
            futures.add(submit_new_request())
            
        # Loop until duration is exceeded
        while time.time() - start_time < duration_seconds:
            # Wait for at least one future to complete
            done, not_done = concurrent.futures.wait(
                futures, 
                timeout=1.0, # Check time every second if nothing finishes
                return_when=concurrent.futures.FIRST_COMPLETED
            )
            
            futures = not_done
            
            for future in done:
                try:
                    res = future.result()
                    results.append(res)
                    status = res[1]
                    # Print output as they complete
                    if str(status).startswith('2'):
                        print(f"[SUCCESS] {status} - {res[2]:.2f}s - {res[0]}")
                    else:
                        print(f"[FAILED] {status} - {res[0]}")
                except Exception as exc:
                    print(f"Request generated an exception: {exc}")
                
                # If we're still within duration, submit a replacement request
                if time.time() - start_time < duration_seconds:
                    futures.add(submit_new_request())
        
        # We've exceeded duration, cancel remaining requests
        for future in futures:
            future.cancel()
                
    total_time = time.time() - start_time
    
    # Print summary statistics
    print("\n--- Load Test Summary ---")
    print(f"Target duration: {duration_seconds} seconds")
    print(f"Actual execution time: {total_time:.2f} seconds")
    print(f"Total requests completed: {len(results)}")
    
    if results:
        success_count = sum(1 for r in results if str(r[1]).startswith('2'))
        print(f"Successful requests (2xx): {success_count}")
        print(f"Failed/Error requests: {len(results) - success_count}")
        print(f"Requests per second (RPS): {len(results) / total_time:.2f}")
        
        avg_time = sum(r[2] for r in results) / len(results)
        print(f"Average response time: {avg_time:.2f} seconds")
    else:
        print("No requests completed.")

if __name__ == "__main__":
    # You can adjust concurrency and duration_seconds here
    run_load_test(concurrency=100, duration_seconds=60)
