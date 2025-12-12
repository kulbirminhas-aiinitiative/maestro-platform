#!/usr/bin/env python3
import json
import os

def create_tickets():
    print("--- AGORA PHASE 2 TICKET CREATION ---")
    
    ticket_file = "docs/roadmap/AGORA_PHASE2_TICKETS.json"
    if not os.path.exists(ticket_file):
        print(f"Error: {ticket_file} not found.")
        return

    with open(ticket_file, 'r') as f:
        tickets = json.load(f)

    print(f"Found {len(tickets)} tickets to create.")
    
    # In a real environment, this would call the JIRA API.
    # Here, we simulate the creation and append to a local backlog file.
    
    backlog_file = "JIRA_BACKLOG_FULL.md"
    
    with open(backlog_file, 'a') as f:
        f.write("\n\n## AGORA PHASE 2 (Generated)\n")
        for t in tickets:
            print(f"Creating {t['key']}: {t['summary']}...")
            f.write(f"- [ ] **{t['key']}**: {t['summary']} (Priority: {t['priority']})\n")
            f.write(f"  - *Description*: {t['description']}\n")
            
    print("--- Tickets successfully added to JIRA_BACKLOG_FULL.md ---")

if __name__ == "__main__":
    create_tickets()
