"""
Agent manager for loading and managing AI agent configurations from agents.json.
"""

import json
import os
from typing import Dict, Any, List


class AgentManager:
    """Manages AI agents and their configurations."""
    
    def __init__(self):
        self.agents_config = self._load_agents_config()
        self.default_agent = self.agents_config.get("default_agent", "general")
    
    def _load_agents_config(self) -> Dict[str, Any]:
        """Load agents configuration from agents.json."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "agents.json")
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading agents config: {e}")
            return {"agents": {}, "tool_categories": {}, "default_agent": "general"}
    
    def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """Get information about a specific agent."""
        agents = self.agents_config.get("agents", {})
        if agent_id in agents:
            return agents[agent_id]
        return {}
    
    def get_agent_system_prompt(self, agent_id: str) -> str:
        """Get the system prompt for a specific agent."""
        agent_info = self.get_agent_info(agent_id)
        return agent_info.get("system_prompt", "")
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent IDs."""
        return list(self.agents_config.get("agents", {}).keys())
    
    def validate_agent(self, agent_id: str) -> bool:
        """Check if an agent exists."""
        return agent_id in self.agents_config.get("agents", {})
    
    def get_all_agents_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all agents."""
        return self.agents_config.get("agents", {})
    
    def get_user_system_prompt(self, user_id: str, channel_id: str) -> str:
        """Get the system prompt for a specific user and channel."""
        try:
            # Get the user's current agent from the agent manager tool
            from app.core.tools.agent_manager import get_agent_manager_tool
            agent_tool = get_agent_manager_tool()
            current_agent_id = agent_tool.get_user_agent(user_id, channel_id)
            
            # Return the system prompt for that agent
            return self.get_agent_system_prompt(current_agent_id)
        except Exception:
            # Fall back to default agent's system prompt
            return self.get_agent_system_prompt(self.default_agent)


# Global instance
_agent_manager = None


def get_agent_manager() -> AgentManager:
    """Get the global agent manager instance."""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager
