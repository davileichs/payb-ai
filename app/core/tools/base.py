"""
Base tool interface for AI chat tools.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ToolResult(BaseModel):
    """Result from a tool execution."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    """Base class for all AI chat tools."""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self._load_schema()
        self.parameters = self._get_parameters()
    
    def _load_schema(self):
        """Load the tool schema from JSON file."""
        try:
            # Get the tool name without 'Tool' suffix for schema file lookup
            tool_name = self.name.replace('Tool', '').lower()
            schema_path = os.path.join(os.path.dirname(__file__), "schemas", f"{tool_name}.json")
            
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    schema = json.load(f)
                    self.description = schema.get("description", "")
                    self._schema_data = schema
                return
            
            # Fallback: try to find schema by exact class name
            schema_path = os.path.join(os.path.dirname(__file__), "schemas", f"{self.name.lower()}.json")
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    schema = json.load(f)
                    self.description = schema.get("description", "")
                    self._schema_data = schema
                return
                
        except Exception as e:
            pass
        
        # Fallback to default values if schema can't be loaded
        self.description = self.__doc__ or "No description available"
        self._schema_data = {}
    
    def _get_parameters(self) -> Dict[str, Any]:
        """Get the tool's parameter schema from the loaded schema file."""
        if hasattr(self, '_schema_data') and self._schema_data:
            return self._schema_data.get("parameters", {})
        return {}
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with the given parameters."""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's schema for AI model consumption."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """Register a new tool."""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all registered tools."""
        return [tool.get_schema() for tool in self._tools.values()]


# Global tool registry
tool_registry = ToolRegistry()


def register_tool(tool: BaseTool):
    """Register a tool in the global registry."""
    tool_registry.register(tool)
