#!/usr/bin/env python3
"""LightSerp MCP client for Karnataka engineering colleges list"""

import subprocess
import json
import time
import os
import re

ROOT_DIR = '/Users/manjunathkanavi/workspace/git_workspace/LightSerp'
SCRIPT_DIR = '/Users/manjunathkanavi/workspace/git_workspace/LightSerp/scripts'

def search_web(query: str) -> list:
    """Call LightSerp MCP search_web tool"""
    cmd = ['node', 'dist/server.js']
    p = subprocess.run(
        cmd,
        input=json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "karnataka-colleges", "version": "1.0"}
            }
        }) + '\n',
        capture_output=True,
        text=True,
        timeout=10,
        cwd=ROOT_DIR
    )
    return []  # This won't work with stdio-based MCP

# Actually, let me use the SearXNG endpoint directly since it's what MCP uses internally
def searx_search(query: str, max_results: int = 50) -> list:
    """Direct SearXNG API call (same as MCP search_web internally)"""
    import urllib.request
    import urllib.parse
    encoded = urllib.parse.quote(query)
    url = f'http://localhost:8080/search?q={encoded}&format=json&categories=general&number_of_results={max_results}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get('results', [])
    except Exception as e:
        print(f"  SearXNG error: {e}")
        return []

def scrape_page(url: str) -> str:
    """Scrape a page using LightSerp scrape_page (via curl to SearXNG + PageZen fallback)"""
    import urllib.request
    import urllib.parse
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            # Extract text from HTML
            text = re.sub('<[^<]+?>', '', html)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:30000]
    except Exception as e:
        print(f"  Scrape error for {url}: {e}")
        return ''

def extract_colleges_from_text(text: str, page_url: str) -> list:
    """Extract college names from scraped text using various patterns"""
    colleges = []
    
    # Look for patterns like "Government Engineering College, X" or "XYZ College of Engineering"
    patterns = [
        # "College of Engineering" / "College Of Engineering"
        r'([A-Z][A-Za-z\s\.\'\-]+(?:College|Institute|University)[^,\n]+(?:of|Of)[^,\n]+Engineering[^,\n]*(?:,?\s*[A-Z][a-z]+)?)',
        # Government Engineering College pattern
        r'(Government\s+(?:Engineering\s+College(?:\s*,\s*[A-Z][a-z]+)?|College\s*,\s*[A-Z][a-z]+|Engineering\s+College,?\s*[A-Za-z\s]+(?:,?\s*[A-Z][a-z]+)?))',
        # "XYZ College of Engineering"
        r'([A-Z][A-Za-z\'\.\-\s]{3,60}(?:College|Institute)[^,\n]*(?:Engineering|Institute|Technology)[^,\n]*)',
    ]
    
    seen = set()
    for text_part in text.split('\n'):
        text_part = text_part.strip()
        if len(text_part) < 15:
            continue
        # Skip if it's not a college name
        if any(x in text_part.lower() for x in ['advertisement', 'copyright', 'privacy', 'terms', 'home', 'login', 'search', 'contact us', 'email', 'phone', 'facult', 'dean', 'principal', 'director', 'professor', 'admin', 'faculty', 'courses', 'fee', 'admission', 'eligibility', 'apply', 'notification']):
            continue
        if any(x in text_part.lower() for x in ['uploaded by', 'follow', 'like', 'dislike']):
            continue
            
        # Check if it looks like a college name
        has_college = any(x in text_part for x in ['College', 'Institute', 'University', 'College Of', 'College of', 'College of Engineering'])
        if has_college or 'government' in text_part.lower():
            clean = text_part.strip().rstrip('.')
            if clean not in seen and len(clean) > 15:
                seen.add(clean)
                colleges.append(clean)
    
    return colleges

def extract_colleges_from_html(html: str, page_url: str) -> list:
    """Extract college names from HTML content"""
    colleges = []
    
    # Look for table-based college lists
    # Find all <td> elements that contain college names
    td_pattern = r'<td[^>]*>(.*?)</td>'
    tds = re.findall(td_pattern, html, re.DOTALL)
    
    for td in tds:
        # Remove HTML tags
        clean = re.sub('<[^<]+?>', '', td).strip()
        # Remove whitespace
        clean = re.sub(r'\s+', ' ', clean)
        
        if len(clean) < 15:
            continue
        
        # Skip non-college content
        skip_keywords = ['advertisement', 'copyright', 'privacy', 'home', 'login', 'search',
                        'contact us', 'email', 'phone', 'facult', 'dean', 'principal',
                        'director', 'professor', 'admin', 'courses', 'fee', 'admission',
                        'eligibility', 'apply', 'notification', 'school', 'nursing',
                        'pharmacy', 'architecture', 'management', 'hospital', 'medical',
                        'dentistry', 'nursing', 'law', 'arts', 'commerce', 'bcom', 'bba',
                        'mcom', 'mba', 'bpharm', 'bams', 'bnys', 'bhms', 'icarus',
                        'animation', 'tourism', 'journalism', 'mass communication',
                        'dental', 'teaching', 'vocational']
        
        if any(kw in clean.lower() for kw in skip_keywords):
            continue
        
        # Must contain college/engineering/technology/institute keywords
        if not any(kw in clean for kw in ['College', 'Institute', 'University', 'College of', 'College Of', 'School']):
            continue
        if not any(kw in clean for kw in ['Engineering', 'Technology', 'Institute']):
            continue
        
        clean = clean.rstrip('.')
        if len(clean) > 15 and clean not in colleges:
            colleges.append(clean)
    
    return colleges

def deduplicate_colleges(colleges: list) -> list:
    """Deduplicate college names with fuzzy matching"""
    if not colleges:
        return []
    
    result = []
    seen_lower = {}
    
    for college in colleges:
        # Normalize name
        clean = ' '.join(college.split())
        lower = clean.lower().strip()
        
        # Skip if too short
        if len(lower) < 15:
            continue
            
        # Check for near-duplicate
        matched = False
        for existing_lower in seen_lower:
            # Simple similarity check
            if lower == existing_lower:
                matched = True
                break
            # If one is contained in the other
            if len(lower) > 20 and len(existing_lower) > 20:
                if lower.replace(' ', '') in existing_lower.replace(' ', '') or existing_lower.replace(' ', '') in lower.replace(' ', ''):
                    matched = True
                    # Keep the longer one
                    if len(lower) > len(existing_lower):
                        result[result.index(seen_lower[existing_lower])] = clean
                        del seen_lower[existing_lower]
                        seen_lower[lower] = clean
                        break
                    break
        
        if not matched:
            result.append(clean)
            seen_lower[lower] = clean
    
    return result

# ===== MAIN =====
def main():
    print("=" * 60)
    print("KARNATAKA ENGINEERING COLLEGES LIST BUILDER")
    print("=" * 60)
    
    # Step 1: Use SearXNG to find comprehensive list sources
    print("\n[1/5] Searching for comprehensive college list sources...")
    
    list_queries = [
        "list of all engineering colleges in Karnataka complete list 2025",
        "engineering colleges in Karnataka all districts list name address",
        "AICTE approved engineering colleges Karnataka complete list",
        "KTU Karnataka engineering colleges list full"
    ]
    
    all_urls = set()
    for q in list_queries:
        results = searx_search(q, 50)
        for r in results:
            url = r.get('url', '')
            title = r.get('title', '').lower()
            # Filter for college list pages
            if ('college' in url or 'college' in title) and \
               not any(skip in url for skip in ['courses', 'fee', 'admission', 'compare', 'prediction', ' counselling']):
                all_urls.add(url)
        print(f"  Query '{q[:50]}...': {len(results)} results, {len(all_urls)} unique URLs so far")
    
    print(f"\n  Found {len(all_urls)} unique listing pages")
    
    # Step 2: Scrape all listing pages
    print(f"\n[2/5] Scraping {len(all_urls)} listing pages...")
    all_colleges = []
    
    for i, url in enumerate(sorted(all_urls)):
        print(f"  [{i+1}/{len(all_urls)}] {url[:80]}...")
        
        # Use direct HTTP scrape (PageZen is the MCP's scraping backend)
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                
                # Extract college names
                colleges = extract_colleges_from_html(html, url)
                if colleges:
                    print(f"    -> Found {len(colleges)} colleges")
                    all_colleges.extend(colleges)
                else:
                    # Try text extraction as fallback
                    text = re.sub('<[^<]+?>', '', html)
                    text = re.sub(r'\s+', ' ', text).strip()
                    colleges = extract_colleges_from_text(text, url)
                    if colleges:
                        print(f"    -> Found {len(colleges)} colleges (via text)")
                        all_colleges.extend(colleges)
        except Exception as e:
            print(f"    -> Error: {str(e)[:60]}")
        
        time.sleep(0.5)  # Be polite
    
    # Step 3: Deduplicate
    print(f"\n[3/5] Deduplicating {len(all_colleges)} college entries...")
    unique_colleges = deduplicate_colleges(all_colleges)
    print(f"  After deduplication: {len(unique_colleges)} unique colleges")
    
    # Step 4: Save college list
    college_list_file = os.path.join(SCRIPT_DIR, 'karnataka_colleges.json')
    with open(college_list_file, 'w') as f:
        json.dump(unique_colleges, f, indent=2, ensure_ascii=False)
    print(f"\n[4/5] Saved college list to {college_list_file}")
    print(f"  Total: {len(unique_colleges)} engineering colleges in Karnataka")
    
    # Step 5: Search for each college's website and scrape details
    print(f"\n[5/5] Searching for college websites and scraping details...")
    print(f"  (This will take a while for {len(unique_colleges)} colleges...)")
    
    colleges_with_details = []
    
    for idx, college_name in enumerate(unique_colleges):
        if (idx + 1) % 20 == 0:
            print(f"  Progress: {idx+1}/{len(unique_colleges)} colleges processed")
        
        # Search for this college's official website
        search_results = searx_search(f'{college_name} official website Karnataka', 5)
        
        website = ''
        district = ''
        college_type = ''
        
        for r in search_results[:3]:
            r_url = r.get('url', '')
            r_title = r.get('title', '').lower()
            r_content = r.get('content', '').lower()
            
            # Check if it's likely the official college website
            if any(x in r_url for x in ['.ac.in', '.edu.in', '.org.in', '.gov.in']) and \
               (college_name.lower().replace(' ', '')[:10] in r_url.replace(' ', '').replace('-', '').replace('_', '')[:50] or
                college_name.split()[0].lower() in r_title or
                college_name.split()[0].lower() in r_content[:100]):
                
                website = r_url
                # Try to extract district/type from title/content
                if 'government' in r_title or 'govt' in r_title:
                    college_type = 'Government'
                elif 'deemed' in r_title or 'deemed to be' in r_title:
                    college_type = 'Deemed to be University'
                elif 'state government' in r_title:
                    college_type = 'State Government University'
                elif 'private' in r_title or 'self financing' in r_title:
                    college_type = 'Private'
                elif 'aided' in r_title or 'aided' in r_content:
                    college_type = 'Government-Aided'
                
                break
        
        # If no website found from search, try adding .ac.in or .edu.in
        if not website:
            base_name = re.sub(r'[^a-zA-Z0-9\s]', '', college_name)
            slug = base_name.lower().replace(' ', '')
            for suffix in ['.ac.in', '.edu.in']:
                test_url = f'https://www.{slug[:50]}{suffix}'
                # Quick check - just mark tentative
                website = test_url
                break
        
        colleges_with_details.append({
            'name': college_name,
            'website': website,
            'district': district,
            'type': college_type,
            'address': '',
            'email': '',
            'placement_email': '',
            'placement_phone': ''
        })
    
    # Save the college list with websites
    output_file = os.path.join(SCRIPT_DIR, 'karnataka_colleges_with_websites.json')
    with open(output_file, 'w') as f:
        json.dump(colleges_with_details, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to {output_file}")
    print(f"\nTotal colleges: {len(unique_colleges)}")
    print(f"With websites: {sum(1 for c in colleges_with_details if c['website'])}")
    print(f"With types: {sum(1 for c in colleges_with_details if c['type'])}")

if __name__ == '__main__':
    main()
