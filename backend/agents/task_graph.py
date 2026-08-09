import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

@dataclass
class TaskNode:
    id: str
    title: str
    agent_type: str
    prompt: str
    depends_on: List[str] = field(default_factory=list)
    status: str = 'pending'
    result: Optional[str] = None
    error: Optional[str] = None

class TaskGraph:
    """A directed acyclic graph (DAG) orchestrator for multi-agent tasks."""
    
    def __init__(self) -> None:
        self.tasks: Dict[str, TaskNode] = {}

    def add_task(self, id: str, title: str, agent_type: str, prompt: str, depends_on: Optional[List[str]] = None) -> TaskNode:
        """Adds a new task node to the graph."""
        try:
            depends_on = depends_on or []
            task = TaskNode(
                id=id,
                title=title,
                agent_type=agent_type,
                prompt=prompt,
                depends_on=depends_on
            )
            self.tasks[id] = task
            return task
        except Exception as e:
            logger.error(f"Error adding task {id}: {e}")
            raise

    def get_task(self, id: str) -> Optional[TaskNode]:
        """Retrieves a task by its ID."""
        return self.tasks.get(id)

    def get_executable_tasks(self) -> List[TaskNode]:
        """Returns pending tasks whose dependencies are all completed."""
        executable = []
        for task in self.tasks.values():
            if task.status == 'pending':
                can_execute = True
                for dep_id in task.depends_on:
                    dep_task = self.tasks.get(dep_id)
                    if not dep_task or dep_task.status != 'completed':
                        can_execute = False
                        break
                if can_execute:
                    executable.append(task)
        return executable

    def mark_completed(self, id: str, result: str) -> None:
        """Marks a task as completed with the given result."""
        try:
            task = self.tasks.get(id)
            if task:
                task.status = 'completed'
                task.result = result
            else:
                logger.warning(f"Task {id} not found to mark completed.")
        except Exception as e:
            logger.error(f"Error marking task {id} as completed: {e}")

    def mark_failed(self, id: str, error: str) -> None:
        """Marks a task as failed with the given error message."""
        try:
            task = self.tasks.get(id)
            if task:
                task.status = 'failed'
                task.error = error
            else:
                logger.warning(f"Task {id} not found to mark failed.")
        except Exception as e:
            logger.error(f"Error marking task {id} as failed: {e}")

    def is_complete(self) -> bool:
        """Checks if all tasks are either completed or failed."""
        if not self.tasks:
            return True
        return all(task.status in ('completed', 'failed') for task in self.tasks.values())

    def has_failed(self) -> bool:
        """Checks if any task has failed."""
        return any(task.status == 'failed' for task in self.tasks.values())

    def format_summary(self) -> str:
        """Returns a formatted status tree summary of all tasks and results."""
        lines = ["Task Graph Summary:"]
        for task in self.tasks.values():
            lines.append(f"- [{task.status.upper()}] {task.id} ({task.title})")
            if task.result:
                lines.append(f"  Result: {task.result}")
            if task.error:
                lines.append(f"  Error: {task.error}")
        return "\n".join(lines)


def create_software_development_dag(project_name: str, requirements: str) -> TaskGraph:
    """Creates a standard 3-stage software development DAG."""
    try:
        graph = TaskGraph()
        
        # 1. Architecture stage
        graph.add_task(
            id="arch",
            title="System Architecture",
            agent_type="analysis",
            prompt=f"Plan file structure and dependencies for project {project_name}. Requirements: {requirements}",
            depends_on=[]
        )
        
        # 2. Implementation stage
        graph.add_task(
            id="code",
            title="Code Implementation",
            agent_type="code",
            prompt="Write code files based on the architecture plan.",
            depends_on=["arch"]
        )
        
        # 3. QA stage
        graph.add_task(
            id="qa",
            title="QA / Verification",
            agent_type="analysis",
            prompt="Verify build and syntax for the implementation.",
            depends_on=["code"]
        )
        
        return graph
    except Exception as e:
        logger.error(f"Error creating software DAG: {e}")
        raise
