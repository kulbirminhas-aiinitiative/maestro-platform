"""
Jupyter Notebook Integration Module

Launch notebooks, auto-save to MLflow, and manage shared workspaces.
"""

from .services.notebook_launcher import NotebookLauncher
from .services.mlflow_integration import MLflowNotebookIntegration
from .services.workspace_manager import WorkspaceManager

__all__ = [
    "NotebookLauncher",
    "MLflowNotebookIntegration",
    "WorkspaceManager",
]
