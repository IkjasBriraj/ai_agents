"""Small local audit trail for sensitive agent decisions.

The log deliberately stores metadata, not file contents, prompts, or model output.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)
AUDIT_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "_audit_events"))
AUDIT_FILE = os.path.join(AUDIT_DIRECTORY, "security.jsonl")


def record_security_event(event: str, **metadata: Any) -> None:
    """Append a best-effort, local-only security event."""
    try:
        os.makedirs(AUDIT_DIRECTORY, exist_ok=True)
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **metadata,
        }
        with open(AUDIT_FILE, "a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("Unable to write security audit event: %s", exc)
