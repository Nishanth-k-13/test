import csv
import os

def extract_urls(filename):
    if not os.path.exists(filename):
        return
    urls = []
    with open(filename, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "url" in row:
                urls.append(row["url"])

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["url"])
        for url in urls:
            writer.writerow([url])
    print(f"Extracted {len(urls)} URLs to {filename}")

extract_urls("tabs_missing.csv")
extract_urls("news_missing.csv")
