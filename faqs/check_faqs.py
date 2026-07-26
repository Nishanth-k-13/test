import csv
import requests
import re
import json
from bs4 import BeautifulSoup

def check_faqs():
    csv_file = '/Users/codingmart/test/faqs/faqs-urls.csv'
    output_file = '/Users/codingmart/test/faqs/faq_report.json'
    
    urls = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    urls.append(row[0].strip())
    except FileNotFoundError:
        print(f"Error: Could not find {csv_file}")
        return

    placeholder_pattern = re.compile(r'\{[a-zA-Z0-9_ &]+\}')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }

    results = []

    for url in urls:
        print(f"Checking {url} ...")
        url_result = {
            'url': url,
            'faq_count': 0,
            'has_exactly_5_faqs': False,
            'placeholders': [],
            'error': None
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            json_lds = soup.find_all('script', type='application/ld+json')
            
            placeholders_found = set()
            faq_count = 0
            
            for script in json_lds:
                if script.string:
                    # Check for placeholders in the raw string
                    found = placeholder_pattern.findall(script.string)
                    placeholders_found.update(found)
                    
                    # Parse JSON to count FAQs
                    try:
                        ld_data = json.loads(script.string)
                        if isinstance(ld_data, dict):
                            if ld_data.get('@type') == 'FAQPage':
                                main_entity = ld_data.get('mainEntity', [])
                                faq_count += len(main_entity)
                        elif isinstance(ld_data, list):
                            for item in ld_data:
                                if isinstance(item, dict) and item.get('@type') == 'FAQPage':
                                    main_entity = item.get('mainEntity', [])
                                    faq_count += len(main_entity)
                    except json.JSONDecodeError:
                        pass
            
            # Also check visible text for placeholders just in case
            visible_found = placeholder_pattern.findall(page_text)
            placeholders_found.update(visible_found)
            
            url_result['faq_count'] = faq_count
            url_result['has_exactly_5_faqs'] = (faq_count == 5)
            url_result['placeholders'] = list(placeholders_found)
                
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            url_result['error'] = str(e)
            
        results.append(url_result)

    print("-" * 50)
    print(f"Total URLs checked: {len(urls)}")
    print("-" * 50)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f"Results saved to {output_file}")
    
    # Save to CSV as well
    csv_output_file = '/Users/codingmart/test/faqs/faq_report.csv'
    if results:
        keys = ['url', 'faq_count', 'has_exactly_5_faqs', 'placeholders', 'error']
        with open(csv_output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in results:
                csv_row = row.copy()
                csv_row['placeholders'] = ', '.join(row['placeholders']) if row['placeholders'] else ''
                writer.writerow(csv_row)
        print(f"Results also saved to {csv_output_file}")
    
    for item in results:
        print(f"\nURL: {item['url']}")
        print(f"FAQ Count: {item['faq_count']} (Exactly 5: {item['has_exactly_5_faqs']})")
        if item['placeholders']:
            print(f"Placeholders Found: {', '.join(item['placeholders'])}")
        if item['error']:
            print(f"Error: {item['error']}")
        print("-" * 30)

if __name__ == "__main__":
    check_faqs()
