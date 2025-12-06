import asyncio
import sys
import os
import markdown

# Add current directory to path to find epic_executor
sys.path.append(os.getcwd())

from epic_executor.confluence.publisher import ConfluencePublisher, ConfluenceConfig

async def main():
    print("🚀 Initializing Confluence Publisher...")
    
    # Configuration
    config = ConfluenceConfig(
        base_url="http://localhost:14000",
        email="admin@maestro.ai", # Dummy email
        api_token="dummy-token",  # Dummy token
        space_key="DS"            # Default space
    )
    
    publisher = ConfluencePublisher(config)
    
    # Get the underlying tool (MinimalConfluenceClient or ConfluenceTool)
    tool = await publisher._get_confluence_tool()
    print(f"✅ Using tool: {type(tool).__name__}")
    
    # Read the Markdown file
    file_path = "MATURITY_ASSESSMENT_AND_ROADMAP.md"
    try:
        with open(file_path, "r") as f:
            md_content = f.read()
    except FileNotFoundError:
        print(f"❌ File {file_path} not found.")
        return

    # Convert Markdown to HTML
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    # Wrap in a macro or div if needed, but raw HTML is usually fine for storage format
    # We'll add a note that it was auto-published
    final_content = f"""
    <p><strong>🚀 Auto-Published by Maestro Self-Reflection Engine</strong></p>
    <hr/>
    {html_content}
    """
    
    print(f"📤 Publishing '{file_path}' to Confluence (Space: {config.space_key})...")
    
    # Try to create the page
    result = await tool.create_page(
        title="Maestro Platform: Maturity Assessment & Strategic Roadmap",
        content=final_content,
        space_key=config.space_key
    )
    
    if result.success:
        print("✅ Successfully published!")
        print(f"   ID: {result.data.get('id')}")
        print(f"   URL: {result.data.get('url')}")
    else:
        print("❌ Failed to publish.")
        print(f"   Error: {result.data.get('error')}")
        
        # Fallback: Try to list spaces to debug
        print("\n🔍 Debugging: Listing spaces...")
        try:
            # MinimalConfluenceClient doesn't have get_spaces, but we can try _api_call if it's exposed
            # or just use the health check
            health = await tool.health_check()
            print(f"   Health Check: {health}")
        except Exception as e:
            print(f"   Debug failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
