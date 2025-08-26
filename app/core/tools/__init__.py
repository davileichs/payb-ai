"""
Tools package for AI chat functionality.
"""

from .weather import WeatherTool
from .provider_handle import ProviderHandle
from .conversation_manager import ConversationManagerTool
from .agent_manager import AgentManagerTool
from .payabl_docs import PayablDocsSearch

# Register all tools
from .base import register_tool

register_tool(WeatherTool())
register_tool(ProviderHandle())
register_tool(ConversationManagerTool())
register_tool(AgentManagerTool())
register_tool(PayablDocsSearch())
