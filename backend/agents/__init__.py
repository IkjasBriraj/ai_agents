"""
Multi-Agent System Module
"""

from .tools import get_tools_for_agent, AGENT_TOOLS
from .specialized_agents import CodeAgent, ResearchAgent, AnalysisAgent
from .orchestrator import OrchestratorAgent

__all__ = [
    'get_tools_for_agent',
    'AGENT_TOOLS',
    'CodeAgent',
    'ResearchAgent',
    'AnalysisAgent',
    'OrchestratorAgent',
]

# Made with Bob
