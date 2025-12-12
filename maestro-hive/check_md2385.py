import asyncio
import logging
from jira_task_adapter import JiraTaskAdapter

# Configure logging
logging.basicConfig(level=logging.INFO)

async def check_ticket(ticket_key):
    adapter = JiraTaskAdapter()
    try:
        task = await adapter.fetch_task(ticket_key)
        if task:
            print(f"Ticket: {task.key}")
            print(f"Summary: {task.summary}")
            print(f"Status: {task.status}")
            print(f"Description:\n{task.description}")
            
            if task.subtasks:
                print("\nSubtasks:")
                for subtask in task.subtasks:
                    print(f"- {subtask}")
        else:
            print(f"Ticket {ticket_key} not found.")
                
    except Exception as e:
        print(f"Error fetching ticket {ticket_key}: {e}")

if __name__ == "__main__":
    child_tasks = ["MD-2468", "MD-2469", "MD-2470", "MD-2471", "MD-2472", "MD-2473", "MD-2474"]
    asyncio.run(check_ticket("MD-2385"))
    print("\n--- Checking Child Tasks ---")
    for task in child_tasks:
        asyncio.run(check_ticket(task))
