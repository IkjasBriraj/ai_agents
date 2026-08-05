import contextvars

# Context variable to store active agent session details (session_id, queue, loop)
current_agent_context = contextvars.ContextVar("current_agent_context", default=None)

# Context variable to accumulate token counts for the active agent execution
current_token_usage = contextvars.ContextVar("current_token_usage", default=None)
