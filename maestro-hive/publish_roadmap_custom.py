import requests
import json
import markdown
import os
import sys

# Configuration - Use environment variables for credentials
BASE_URL = os.environ.get("MAESTRO_BACKEND_URL", "http://localhost:14000")
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
CONFLUENCE_API_URL = f"{BASE_URL}/api/confluence"
USERNAME = os.environ.get("MAESTRO_ADMIN_EMAIL", "admin@maestro.com")
PASSWORD = os.environ.get("MAESTRO_ADMIN_PASSWORD")  # Required - no default
SPACE_KEY = os.environ.get("CONFLUENCE_SPACE_KEY", "MD")  # MD is authoritative space
PARENT_PAGE_ID = os.environ.get("CONFLUENCE_PARENT_PAGE_ID")
PAGE_TITLE = "Maestro Platform Maturity Assessment & Roadmap"
FILE_PATH = "/home/ec2-user/projects/maestro-platform/maestro-hive/MATURITY_ASSESSMENT_AND_ROADMAP.md"

def login():
    if not PASSWORD:
        print("Error: MAESTRO_ADMIN_PASSWORD environment variable is required.")
        print("Usage: MAESTRO_ADMIN_PASSWORD=<password> python3 publish_roadmap_custom.py")
        sys.exit(1)

    print(f"Logging in as {USERNAME}...")
    try:
        response = requests.post(LOGIN_URL, json={"email": USERNAME, "password": PASSWORD})
        if response.status_code != 200:
            raise Exception(f"Login failed: {response.text}")
        token = response.json()["data"]["tokens"]["accessToken"]
        print("Login successful.")
        return token
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {BASE_URL}. Is the backend server running?")
        sys.exit(1)

def read_markdown_file(file_path):
    if not os.path.exists(file_path):
        raise Exception(f"File not found: {file_path}")
    with open(file_path, "r") as f:
        return f.read()

def convert_to_html(markdown_content):
    # Convert Markdown to HTML
    # We use extra extensions for better formatting
    html = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code', 'nl2br'])
    return html

def publish_page(token, title, content_html, space_key, parent_id):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # First, check if page exists to update it, or create new
    # Search for page by title (using contains ~ to avoid special char issues)
    search_url = f"{CONFLUENCE_API_URL}/search"
    # Remove special chars for search
    safe_title = title.replace("&", "").replace("  ", " ")
    cql = f"space = \"{space_key}\" AND title ~ \"{safe_title}\""
    print(f"Searching for existing page: {title}...")
    
    try:
        search_response = requests.post(search_url, headers=headers, json={"cql": cql})
        
        page_id = None
        version = 1
        
        if search_response.status_code == 200:
            results = search_response.json().get("results", [])
            if results:
                page_id = results[0]["id"]
                # Check if version info is available, otherwise default to 1
                if "version" in results[0]:
                    version = results[0]["version"]["number"] + 1
                print(f"Found existing page ID: {page_id}, next version: {version}")
        else:
            print(f"Search failed: {search_response.status_code} - {search_response.text}")
            # Continue to try creating if search fails? No, might duplicate.
            
        if page_id:
            # Update existing page
            update_url = f"{CONFLUENCE_API_URL}/page/{page_id}"
            payload = {
                "title": title,
                "body": content_html, 
                "version": version
            }
            print(f"Updating page {page_id}...")
            response = requests.put(update_url, headers=headers, json=payload)
        else:
            # Create new page
            create_url = f"{CONFLUENCE_API_URL}/page"
            payload = {
                "spaceKey": space_key,
                "title": title,
                "body": content_html,
                "parentId": parent_id
            }
            print("Creating new page...")
            response = requests.post(create_url, headers=headers, json=payload)
            
        if response.status_code in [200, 201]:
            print("Successfully published page!")
            data = response.json()
            # Construct link
            if "_links" in data and "webui" in data["_links"]:
                # This is a guess at the base URL for the frontend, usually port 3000 or 80
                # But the backend returns a relative link
                print(f"Page Link: {data['_links']['webui']}")
            return data
        else:
            print(f"Failed to publish page: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def main():
    try:
        # Check if we are in the right directory
        if not os.path.exists(FILE_PATH):
            # Try to find it in the current directory or subdirectories
            print(f"Warning: {FILE_PATH} not found in current directory.")
            # Assuming we are in maestro-hive root
            pass

        token = login()
        markdown_content = read_markdown_file(FILE_PATH)
        html_content = convert_to_html(markdown_content)
        publish_page(token, PAGE_TITLE, html_content, SPACE_KEY, PARENT_PAGE_ID)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
