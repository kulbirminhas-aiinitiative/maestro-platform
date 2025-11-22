# Overview of AI Team Structures

This document outlines the different types of AI agent teams that can be orchestrated using the Claude Team SDK. Each structure offers different benefits depending on the project's complexity and goals.

## 1. Static Team (Sequential Workflow)

A Static Team is composed of a fixed set of agents that collaborate on a task, often in a predictable, sequential order. This is the most basic team structure.

- **Composition**: Fixed number of agents with predefined roles.
- **Workflow**: Typically sequential, where the output of one agent becomes the input for the next. For example, an architect designs a system, a developer implements it, and a reviewer checks the code.
- **Use Case**: Simple, well-defined projects where the workflow is linear and known in advance.

**Example**: `example_static_team.py` demonstrates a simple workflow where an analyst writes a report and a reviewer checks it.

## 2. Parallel Team

A Parallel Team consists of multiple agents working on different, independent sub-tasks concurrently. This structure is designed to improve efficiency by executing tasks in parallel.

- **Composition**: Can be static or dynamic, but the key is that multiple agents can work simultaneously without blocking each other.
- **Workflow**: A central coordinator assigns tasks to multiple agents (e.g., multiple developers) who can work at the same time. The system uses `asyncio` to manage concurrent operations.
- **Use Case**: Large tasks that can be broken down into smaller, independent units of work. For example, developing multiple, unrelated microservices at the same time.

**Example**: `example_parallel_team.py` shows two "researcher" agents analyzing different topics concurrently.

## 3. Dynamic/Elastic Team

A Dynamic or Elastic Team is the most advanced structure. The team's composition can change during the project's lifecycle. Agents can be added or removed based on the project's needs.

- **Composition**: Flexible. Agents are added "just-in-time" to address a specific need and can be retired when their task is complete.
- **Workflow**: Highly adaptive. A `DynamicTeamManager` orchestrates the team, using features like AI-powered onboarding for new agents and knowledge handoffs for departing agents.
- **Use Case**: Complex, long-running projects with evolving requirements. This model optimizes for cost and expertise by only engaging agents when they are needed.

**Example**: `example_dynamic_team.py` showcases a team that starts with a project manager, adds a developer to write code, and then retires the developer after the task is done.
