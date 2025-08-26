"""
Agent manager tool for handling AI agent switching and management.
"""

from typing import Dict, Any
from app.core.tools.base import BaseTool, ToolResult, register_tool
from app.core.agents import get_agent_manager


class AgentManagerTool(BaseTool):
    """
    A tool for managing AI agents and switching between them.
    """
    
    def __init__(self):
        super().__init__()
        # Internal storage for user agent preferences
        self._user_agents = {}
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the agent manager tool."""
        try:
            action = kwargs.get("action", "current")
            agent_id = kwargs.get("agent_id")
            user_id = kwargs.get("user_id")
            channel_id = kwargs.get("channel_id")
            
            agent_manager = get_agent_manager()
            
            if action == "switch":
                if not agent_id or not user_id or not channel_id:
                    return ToolResult(
                        success=False,
                        error="Agent ID, user_id, and channel_id parameters are required for switch action",
                        metadata={"tool_name": "AgentManager"}
                    )
                
                result = await self._switch_agent(agent_manager, agent_id, user_id, channel_id)
                return result
                
            elif action == "list":
                result = self._list_agents(agent_manager)
                return result
                
            elif action == "current":
                if not user_id or not channel_id:
                    return ToolResult(
                        success=False,
                        error="User_id and channel_id parameters are required for current action",
                        metadata={"tool_name": "AgentManager"}
                    )
                result = self._get_current_agent(agent_manager, user_id, channel_id)
                return result
                
            elif action == "info":
                if not agent_id:
                    return ToolResult(
                        success=False,
                        error="Agent ID parameter is required for info action",
                        metadata={"tool_name": "AgentManager"}
                    )
                result = self._get_agent_info(agent_manager, agent_id)
                return result
                
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    metadata={"tool_name": "AgentManager"}
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool_name": "AgentManager"}
            )
    
    async def _switch_agent(self, agent_manager, agent_id: str, user_id: str, channel_id: str) -> ToolResult:
        """Switch to a different AI agent for a specific user and channel."""
        try:
            # Validate agent
            if not agent_manager.validate_agent(agent_id):
                return ToolResult(
                    success=False,
                    error=f"Agent '{agent_id}' not found. Available: {agent_manager.get_available_agents()}",
                    metadata={"tool_name": "AgentManager"}
                )
            
            # Get agent information
            agent_info = agent_manager.get_agent_info(agent_id)
            
            # Store the user's agent preference
            key = f"{user_id}:{channel_id}"
            self._user_agents[key] = agent_id
            
            return ToolResult(
                success=True,
                data={
                    "message": f"Successfully switched to {agent_info['name']} agent",
                    "agent_id": agent_id,
                    "agent_name": agent_info["name"],
                    "description": agent_info["description"],
                    "tools": agent_info["tools"],
                    "action": "agent_switch"
                },
                metadata={"tool_name": "AgentManager", "agent_switch": True, "new_agent_id": agent_id}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to switch agent: {str(e)}",
                metadata={"tool_name": "AgentManager"}
            )
    
    def _list_agents(self, agent_manager) -> ToolResult:
        """List available AI agents."""
        try:
            agents_info = agent_manager.get_all_agents_info()
            
            return ToolResult(
                success=True,
                data={
                    "agents": agents_info,
                    "total_agents": len(agents_info)
                },
                metadata={"tool_name": "AgentManager"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to list agents: {str(e)}",
                metadata={"tool_name": "AgentManager"}
            )
    
    def _get_current_agent(self, agent_manager, user_id: str, channel_id: str) -> ToolResult:
        """Get current agent information for a specific user and channel."""
        try:
            key = f"{user_id}:{channel_id}"
            current_agent_id = self._user_agents.get(key, agent_manager.default_agent)
            agent_info = agent_manager.get_agent_info(current_agent_id)
            
            return ToolResult(
                success=True,
                data={
                    "current_agent": current_agent_id,
                    "agent_info": agent_info
                },
                metadata={"tool_name": "AgentManager"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to get current agent: {str(e)}",
                metadata={"tool_name": "AgentManager"}
            )
    
    def _get_agent_info(self, agent_manager, agent_id: str) -> ToolResult:
        """Get information about a specific agent."""
        try:
            if not agent_manager.validate_agent(agent_id):
                return ToolResult(
                    success=False,
                    error=f"Agent '{agent_id}' not found",
                    metadata={"tool_name": "AgentManager"}
                )
            
            agent_info = agent_manager.get_agent_info(agent_id)
            
            return ToolResult(
                success=True,
                data={
                    "agent_id": agent_id,
                    "agent_info": agent_info
                },
                metadata={"tool_name": "AgentManager"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to get agent info: {str(e)}",
                metadata={"tool_name": "AgentManager"}
            )
    
    def get_user_agent(self, user_id: str, channel_id: str) -> str:
        """Get the current agent for a specific user and channel."""
        key = f"{user_id}:{channel_id}"
        return self._user_agents.get(key, "general")


# Register the tool automatically
_agent_manager_tool = AgentManagerTool()
register_tool(_agent_manager_tool)


def get_agent_manager_tool() -> AgentManagerTool:
    """Get the global agent manager tool instance."""
    return _agent_manager_tool
