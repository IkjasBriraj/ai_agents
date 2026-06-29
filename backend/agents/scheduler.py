"""
Background Scheduler
Runs scheduled/looped tasks automatically on their timer intervals.
The scheduler runs as an asyncio background task started at application startup.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from .config import DEFAULT_MAIN_MODEL

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """
    Periodically checks for due scheduled tasks and executes them
    through the orchestrator agent pipeline.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MAIN_MODEL,
        ollama_base_url: str = "http://localhost:11434",
        poll_interval: int = 30  # Check every 30 seconds
    ):
        self.model_name = model_name
        self.ollama_base_url = ollama_base_url
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background scheduling loop"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("BackgroundScheduler started (poll every %ds)", self.poll_interval)

    async def stop(self):
        """Stop the background scheduling loop"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("BackgroundScheduler stopped")

    async def _run_loop(self):
        """Main polling loop"""
        while self._running:
            try:
                await self._check_and_run_due_tasks()
            except Exception as e:
                logger.error("Scheduler loop error: %s", e, exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def _check_and_run_due_tasks(self):
        """Query for tasks that are due and execute them"""
        from database.db import SessionLocal
        from database.models import ScheduledTaskModel

        session = SessionLocal()
        task_ids = []
        try:
            now = datetime.utcnow()
            due_tasks = session.query(ScheduledTaskModel).filter(
                ScheduledTaskModel.status == "active",
                ScheduledTaskModel.run_at <= now
            ).all()
            task_ids = [t.id for t in due_tasks]
        except Exception as e:
            logger.error("Error checking due tasks: %s", e, exc_info=True)
        finally:
            session.close()

        # Run tasks outside the polling session
        for task_id in task_ids:
            logger.info("Executing scheduled task ID: %s", task_id)
            await self._execute_task(task_id)

    async def _execute_task(self, task_id: str):
        """Execute a single scheduled task through the orchestrator"""
        from database.db import SessionLocal
        from database.models import ScheduledTaskModel
        from sqlalchemy.orm.attributes import flag_modified

        # 1. Update status to running and close session immediately
        session = SessionLocal()
        prompt = ""
        task_name = ""
        try:
            task = session.query(ScheduledTaskModel).filter(ScheduledTaskModel.id == task_id).first()
            if not task:
                logger.error("Task %s not found in database", task_id)
                return
            task_name = task.name
            task.status = "running"
            session.commit()
            prompt = task.prompt
        except Exception as e:
            logger.error("Error marking task %s as running: %s", task_id, e)
            return
        finally:
            session.close()

        # 2. Run the orchestrator in a thread (no session held open!)
        status = "success"
        summary = "No response"
        try:
            result = await asyncio.to_thread(self._run_orchestrator, prompt, task_id)
            if isinstance(result, dict):
                summary = result.get("response", str(result))[:500]
            elif isinstance(result, str):
                summary = result[:500]
        except Exception as e:
            status = "error"
            summary = str(e)[:500]
            logger.error("Error executing scheduled task '%s' via orchestrator: %s", task_name, e, exc_info=True)

        # 3. Record results in a new session
        session = SessionLocal()
        try:
            task = session.query(ScheduledTaskModel).filter(ScheduledTaskModel.id == task_id).first()
            if task:
                # Log to history
                history = list(task.history or [])
                history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": status,
                    "summary": summary
                })
                if len(history) > 50:
                    history = history[-50:]
                
                task.history = history
                task.last_run = datetime.utcnow()
                flag_modified(task, "history")

                # Determine next run
                if task.interval_minutes and task.interval_minutes > 0:
                    task.run_at = datetime.utcnow() + timedelta(minutes=task.interval_minutes)
                    task.status = "active"
                else:
                    task.status = "completed"
                
                session.commit()
                logger.info("Scheduled task '%s' execution finished with status: %s", task_name, status)
        except Exception as e:
            logger.error("Error saving scheduled task %s results: %s", task_id, e)
        finally:
            session.close()

    def _run_orchestrator(self, prompt: str, task_id: str) -> dict:
        """
        Synchronously run the orchestrator agent.
        Called from asyncio.to_thread to avoid blocking.
        For scheduled tasks, the agent has full access (no permission restrictions).
        """
        from .orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent(self.model_name, self.ollama_base_url)
        session_id = f"scheduled_{task_id}"

        result = orchestrator.process_request(
            prompt,
            context={"scheduled": True, "unrestricted": True},
            session_id=session_id
        )
        return result


# Singleton scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler(
    model_name: str = DEFAULT_MAIN_MODEL,
    ollama_base_url: str = "http://localhost:11434"
) -> BackgroundScheduler:
    """Get or create the singleton scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(model_name, ollama_base_url)
    return _scheduler
