#!/usr/bin/env python3
import os

def update_backlog():
    source_file = "docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md"
    target_file = "JIRA_BACKLOG_FULL.md"
    
    if not os.path.exists(source_file):
        print(f"Error: {source_file} not found.")
        return

    with open(source_file, 'r') as f:
        new_content = f.read()

    print(f"Reading detailed backlog from {source_file}...")
    
    # Append to the main backlog
    with open(target_file, 'a') as f:
        f.write("\n\n" + "="*40 + "\n")
        f.write("AGORA PHASE 2 DETAILED SPECIFICATIONS (UPDATED)\n")
        f.write("="*40 + "\n\n")
        f.write(new_content)
            
    print(f"✅ Successfully updated {target_file} with detailed specifications.")
    print("The tickets are now ready for AI Agent consumption.")

if __name__ == "__main__":
    update_backlog()
