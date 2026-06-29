import asyncio
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Registry of pending permission requests
# Structure: session_id -> { key: (asyncio.Event, decision_dict, loop) }
# where decision_dict is {"granted": bool, "resolved": bool}
_pending_permissions: Dict[str, Dict[str, Tuple[asyncio.Event, Dict[str, Any], asyncio.AbstractEventLoop]]] = {}

def resolve_permission(session_id: str, path: str, granted: bool) -> bool:
    """Set the event and record the decision from the user"""
    if session_id in _pending_permissions and path in _pending_permissions[session_id]:
        event, decision, loop = _pending_permissions[session_id][path]
        decision["granted"] = granted
        decision["resolved"] = True
        
        # Trigger event.set() thread-safely in the loop thread
        loop.call_soon_threadsafe(event.set)
        return True
    return False

def resolve_command_permission(session_id: str, command: str, granted: bool) -> bool:
    """Set the event and record the decision for a command permission request"""
    key = f"cmd:{command}"
    if session_id in _pending_permissions and key in _pending_permissions[session_id]:
        event, decision, loop = _pending_permissions[session_id][key]
        decision["granted"] = granted
        decision["resolved"] = True
        
        loop.call_soon_threadsafe(event.set)
        return True
    return False

def register_and_wait_for_permission(
    session_id: str,
    path: str,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
    timeout: float = 60.0
) -> bool:
    """
    Registers a request, pushes it to the frontend queue,
    and blocks the current thread waiting for the main event loop to set the event.
    """
    # Create the Event on the running loop thread-safely
    async def create_event():
        return asyncio.Event()
        
    future_event = asyncio.run_coroutine_threadsafe(create_event(), loop)
    try:
        event = future_event.result(timeout=5.0)
    except Exception as e:
        logger.error(f"Failed to create asyncio.Event in loop thread: {e}")
        event = asyncio.Event() # fallback
        
    decision = {"granted": False, "resolved": False}
    
    if session_id not in _pending_permissions:
        _pending_permissions[session_id] = {}
    _pending_permissions[session_id][path] = (event, decision, loop)
    
    # Yield the permission request to the frontend stream
    loop.call_soon_threadsafe(
        queue.put_nowait,
        {
            "type": "permission_request",
            "permission_type": "path",
            "path": path,
            "session_id": session_id,
            "done": False
        }
    )
    
    logger.info(f"Permission request sent for path: {path}. Waiting up to {timeout}s...")
    
    # Wait for the event in the main loop thread-safely
    async def wait_coro():
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return decision.get("granted", False)
        except asyncio.TimeoutError:
            logger.warning(f"Permission request timed out for path: {path}")
            return False
            
    future = asyncio.run_coroutine_threadsafe(wait_coro(), loop)
    
    try:
        # Blocks the current tool execution thread until resolved
        result = future.result(timeout=timeout + 2.0)
        return result
    except Exception as e:
        logger.error(f"Error waiting for permission: {e}")
        return False
    finally:
        # Clean up the entry
        if session_id in _pending_permissions and path in _pending_permissions[session_id]:
            try:
                del _pending_permissions[session_id][path]
            except KeyError:
                pass


def register_and_wait_for_command_permission(
    session_id: str,
    command: str,
    cwd: str,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
    timeout: float = 120.0
) -> bool:
    """
    Registers a command execution permission request, pushes it to the frontend queue,
    and blocks the current thread waiting for user approval.
    """
    async def create_event():
        return asyncio.Event()

    future_event = asyncio.run_coroutine_threadsafe(create_event(), loop)
    try:
        event = future_event.result(timeout=5.0)
    except Exception as e:
        logger.error(f"Failed to create asyncio.Event for command permission: {e}")
        event = asyncio.Event()

    decision = {"granted": False, "resolved": False}
    key = f"cmd:{command}"

    if session_id not in _pending_permissions:
        _pending_permissions[session_id] = {}
    _pending_permissions[session_id][key] = (event, decision, loop)

    # Yield the command permission request to the frontend stream
    loop.call_soon_threadsafe(
        queue.put_nowait,
        {
            "type": "permission_request",
            "permission_type": "command",
            "command": command,
            "cwd": cwd,
            "session_id": session_id,
            "done": False
        }
    )

    logger.info(f"Command permission request sent: '{command}' in '{cwd}'. Waiting up to {timeout}s...")

    async def wait_coro():
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return decision.get("granted", False)
        except asyncio.TimeoutError:
            logger.warning(f"Command permission request timed out: {command}")
            return False

    future = asyncio.run_coroutine_threadsafe(wait_coro(), loop)

    try:
        result = future.result(timeout=timeout + 2.0)
        return result
    except Exception as e:
        logger.error(f"Error waiting for command permission: {e}")
        return False
    finally:
        if session_id in _pending_permissions and key in _pending_permissions[session_id]:
            try:
                del _pending_permissions[session_id][key]
            except KeyError:
                pass
