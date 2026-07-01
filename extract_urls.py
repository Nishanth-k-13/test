import csv

urls = []
with open("content_missing.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        urls.append(row["url"])

with open("content_missing.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["url"])
    for url in urls:
        writer.writerow([url])

print(f"Extracted {len(urls)} URLs to content_missing.csv")
