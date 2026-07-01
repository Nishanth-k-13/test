import json

content_missing = []
news_missing = []
tabs_missing = []

with open('missing_data_report.jsonl', 'r') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            data = json.loads(line)
            msg = data.get("missing_section", "")
            
            if "News - No News Articles" in msg:
                news_missing.append(data)
            elif "Tab Missing" in msg or "Header Missing" in msg or "Page Load Error" in msg:
                tabs_missing.append(data)
            else:
                # FAQs, SEO Content, Fundamentals Content Failed, F&O missing data, etc.
                content_missing.append(data)
        except Exception as e:
            pass

with open('content_missing.json', 'w') as f:
    json.dump(content_missing, f, indent=4)

with open('news_missing.json', 'w') as f:
    json.dump(news_missing, f, indent=4)

with open('tabs_missing.json', 'w') as f:
    json.dump(tabs_missing, f, indent=4)

print(f"Split complete: {len(content_missing)} content missing, {len(news_missing)} news missing, {len(tabs_missing)} tabs missing.")
