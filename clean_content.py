import json
import csv

with open("content_missing.json", "r") as f:
    data = json.load(f)

unique_data = []
seen_urls = set()

for item in data:
    url = item.get("url")
    missing_section = item.get("missing_section", "")
    
    # Skip the FAQ errors as requested
    if "FAQs - Expected 5 FAQs" in missing_section:
        continue
        
    if url not in seen_urls:
        unique_data.append(item)
        seen_urls.add(url)

with open("content_missing.json", "w") as f:
    json.dump(unique_data, f, indent=4)

with open("content_missing.csv", "w", newline="") as f:
    if unique_data:
        writer = csv.DictWriter(f, fieldnames=unique_data[0].keys())
        writer.writeheader()
        for row in unique_data:
            writer.writerow(row)
    else:
        # If empty, just write header
        writer = csv.DictWriter(f, fieldnames=["url", "missing_section"])
        writer.writeheader()

print(f"Removed FAQ errors and duplicates. Reduced from {len(data)} to {len(unique_data)} entries.")
