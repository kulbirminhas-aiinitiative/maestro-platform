"""
Example: Using the ML Pipeline API via HTTP client
"""

import requests
import time
import json
import os


class MLPipelineClient:
    """Client for ML Pipeline Orchestration API"""

    def __init__(self, base_url: str = None):
        if base_url is None:
            host = os.getenv("API_HOST", "localhost")
            port = os.getenv("API_PORT", "8000")
            base_url = f"http://{host}:{port}"
        self.base_url = base_url

    def health_check(self):
        """Check API health"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()

    def create_workflow(self, workflow_config: dict):
        """Create a new workflow"""
        response = requests.post(
            f"{self.base_url}/workflows",
            json=workflow_config
        )
        return response.json()

    def list_workflows(self):
        """List all workflows"""
        response = requests.get(f"{self.base_url}/workflows")
        return response.json()

    def get_workflow(self, workflow_id: str):
        """Get workflow details"""
        response = requests.get(f"{self.base_url}/workflows/{workflow_id}")
        return response.json()

    def execute_workflow(self, workflow_id: str):
        """Execute a workflow"""
        response = requests.post(
            f"{self.base_url}/workflows/{workflow_id}/execute"
        )
        return response.json()

    def get_workflow_status(self, workflow_id: str):
        """Get workflow execution status"""
        response = requests.get(
            f"{self.base_url}/workflows/{workflow_id}/status"
        )
        return response.json()

    def visualize_workflow(self, workflow_id: str):
        """Get workflow visualization"""
        response = requests.get(
            f"{self.base_url}/workflows/{workflow_id}/visualize"
        )
        return response.json()

    def list_executions(self):
        """List all executions"""
        response = requests.get(f"{self.base_url}/executions")
        return response.json()

    def get_execution(self, execution_id: str):
        """Get execution details"""
        response = requests.get(f"{self.base_url}/executions/{execution_id}")
        return response.json()


def main():
    """Example usage of API client"""

    # Initialize client
    client = MLPipelineClient()

    # Health check
    print("Checking API health...")
    health = client.health_check()
    print(f"API Status: {health['status']}")
    print()

    # Create workflow
    print("Creating workflow...")
    workflow_config = {
        "name": "API Example Workflow",
        "description": "Testing workflow via API",
        "tasks": [
            {
                "task_id": "task1",
                "name": "Data Processing",
                "task_type": "data_processing",
                "dependencies": [],
                "parameters": {"record_count": 1000}
            },
            {
                "task_id": "task2",
                "name": "Model Training",
                "task_type": "model_training",
                "dependencies": ["task1"],
                "parameters": {}
            },
            {
                "task_id": "task3",
                "name": "Evaluation",
                "task_type": "model_evaluation",
                "dependencies": ["task2"],
                "parameters": {}
            }
        ],
        "max_parallel_tasks": 2
    }

    workflow = client.create_workflow(workflow_config)
    workflow_id = workflow["workflow_id"]
    print(f"Workflow created: {workflow_id}")
    print()

    # List workflows
    print("Listing workflows...")
    workflows = client.list_workflows()
    print(f"Total workflows: {len(workflows)}")
    print()

    # Visualize workflow
    print("Getting workflow visualization...")
    viz = client.visualize_workflow(workflow_id)
    print(f"Nodes: {len(viz['dag']['nodes'])}")
    print(f"Critical path: {viz['critical_path']}")
    print()

    # Execute workflow
    print("Executing workflow...")
    exec_result = client.execute_workflow(workflow_id)
    print(f"Execution started: {exec_result['status']}")
    print()

    # Poll for status
    print("Polling for status...")
    for i in range(10):
        time.sleep(2)
        status = client.get_workflow_status(workflow_id)
        print(f"Status: {status['status']}, Progress: {status.get('progress', {})}")

        if status['status'] not in ['pending', 'running']:
            break
    print()

    # Get final execution results
    print("Listing executions...")
    executions = client.list_executions()
    if executions:
        latest_execution = executions[0]
        print(f"Latest execution: {latest_execution['execution_id']}")
        print(f"Status: {latest_execution['status']}")
        print(f"Progress: {latest_execution['progress']}")


if __name__ == "__main__":
    main()