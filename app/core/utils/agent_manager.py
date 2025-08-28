import json
import os
from typing import Dict, Any, List

class AgentManager:
    
    def __init__(self):
        self.agents_config = self._load_agents_config()
        self.default_agent = self.agents_config.get("default_agent", "general")
    
    def _load_agents_config(self) -> Dict[str, Any]:
        try:
            # Look for agents.json in the project root
            # From app/core/agents/agent_manager.py -> app/core/agents -> app/core -> app -> project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            config_path = os.path.join(project_root, "agents.json")
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading agents config: {e}")
            return {"agents": {}, "tool_categories": {}, "default_agent": "general"}
    
    def reload_agents_config(self) -> bool:
        """Reload the agents configuration from file"""
        try:
            old_config = self.agents_config
            self.agents_config = self._load_agents_config()
            self.default_agent = self.agents_config.get("default_agent", "general")
            print(f"Agents config reloaded successfully")
            return True
        except Exception as e:
            print(f"Error reloading agents config: {e}")
            # Restore old config if reload failed
            self.agents_config = old_config
            return False
    
    def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        agents = self.agents_config.get("agents", {})
        if agent_id in agents:
            return agents[agent_id]
        return {}
    
    def get_agent_system_prompt(self, agent_id: str) -> str:
        agent_info = self.get_agent_info(agent_id)
        return agent_info.get("system_prompt", "")
    
    def get_available_agents(self) -> List[str]:
        return list(self.agents_config.get("agents", {}).keys())
    
    def validate_agent(self, agent_id: str) -> bool:
        return agent_id in self.agents_config.get("agents", {})
    
    def get_all_agents_info(self) -> Dict[str, Dict[str, Any]]:
        return self.agents_config.get("agents", {})
    
    def get_user_system_prompt(self, user_id: str, channel_id: str) -> str:
        try:
            from app.core.tools.agent_manager import get_agent_manager_tool
            agent_tool = get_agent_manager_tool()
            current_agent_id = agent_tool.get_user_agent(user_id, channel_id)
            
            # Return the system prompt for that agent
            return self.get_agent_system_prompt(current_agent_id)
        except Exception:
            # Fall back to default agent's system prompt
            return self.get_agent_system_prompt(self.default_agent)
    
    def get_agent_tools(self, agent_id: str) -> List[str]:
        agent_info = self.get_agent_info(agent_id)
        if not agent_info:
            return []
        
        tool_categories = agent_info.get("tools", [])
        all_tools = []
        
        for category in tool_categories:
            category_tools = self.agents_config.get("tool_categories", {}).get(category, [])
            all_tools.extend(category_tools)
        
        return all_tools
    
    def get_user_tools(self, user_id: str, channel_id: str) -> List[str]:
        try:
            from app.core.tools.agent_manager import get_agent_manager_tool
            agent_tool = get_agent_manager_tool()
            current_agent_id = agent_tool.get_user_agent(user_id, channel_id)
            
            # Return the tools for that agent
            return self.get_agent_tools(current_agent_id)
        except Exception:
            # Fall back to default agent's tools
            return self.get_agent_tools(self.default_agent)

_agent_manager = None

def get_agent_manager() -> AgentManager:
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager
