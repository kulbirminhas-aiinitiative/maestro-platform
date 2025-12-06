import requests
import markdown
import json
import sys
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:14000"
SPACE_KEY = "DS" # Default space
TITLE = "Maestro Platform: Maturity Assessment & Strategic Roadmap"
FILE_PATH = "MATURITY_ASSESSMENT_AND_ROADMAP.md"

def convert_md_to_html(md_content):
    # Convert Markdown to HTML
    html = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    # Wrap in Confluence storage format structure if needed, but usually plain HTML is accepted if we specify representation='storage'
    # However, Confluence is picky about valid XHTML.
    # For simplicity, we'll trust the markdown library produces valid HTML fragments.
    return html

def find_endpoint():
    candidates = [
        "/wiki/rest/api/content",
        "/rest/api/content",
        "/api/confluence/pages",
        "/confluence/pages",
        "/pages",
        "/api/pages"
    ]
    
    print(f"🔍 Probing {BASE_URL} for Confluence API...")
    
    # Try to list spaces or content to verify endpoint
    for endpoint in candidates:
        url = f"{BASE_URL}{endpoint}"
        print(f"  Probing {url}...")
        try:
            # Try a GET request first (listing content)
            response = requests.get(url, timeout=2)
            if response.status_code != 404:
                print(f"  ✅ Found potential endpoint: {endpoint} (Status: {response.status_code})")
                return endpoint
            
            # If GET fails (e.g. method not allowed), try POST with empty body to see if we get a validation error instead of 404
            response = requests.post(url, json={}, timeout=2)
            if response.status_code != 404:
                print(f"  ✅ Found potential endpoint: {endpoint} (Status: {response.status_code})")
                return endpoint
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Connection error: {e}")
            continue
            
    return None

def publish_page(endpoint, html_content):
    url = f"{BASE_URL}{endpoint}"
    
    payload = {
        "title": TITLE,
        "type": "page",
        "space": {"key": SPACE_KEY},
        "body": {
            "storage": {
                "value": html_content,
                "representation": "storage"
            }
        }
    }
    
    print(f"🚀 Publishing to {url}...")
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code in [200, 201]:
            data = response.json()
            print("✅ Successfully published!")
            print(f"   ID: {data.get('id')}")
            print(f"   Link: {data.get('_links', {}).get('webui')}")
            return True
        else:
            print(f"❌ Failed to publish. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error publishing: {e}")
        return False

def main():
    # 1. Read File
    try:
        with open(FILE_PATH, 'r') as f:
            md_content = f.read()
    except FileNotFoundError:
        print(f"❌ File {FILE_PATH} not found.")
        sys.exit(1)

    # 2. Convert
    html_content = convert_md_to_html(md_content)
    
    # 3. Find Endpoint
    endpoint = find_endpoint()
    
    if not endpoint:
        print("❌ Could not find a valid Confluence API endpoint on port 14000.")
        # Fallback: Try the standard one anyway
        endpoint = "/wiki/rest/api/content"
        print(f"⚠️  Falling back to standard endpoint: {endpoint}")

    # 4. Publish
    publish_page(endpoint, html_content)

if __name__ == "__main__":
    main()
