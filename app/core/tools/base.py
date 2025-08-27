import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ToolResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BaseTool(ABC):
    
    def __init__(self):
        self.name = self.__class__.__name__
        self._load_schema()
        self.parameters = self._get_parameters()
    
    def _load_schema(self):
        try:
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
        
        self.description = self.__doc__ or "No description available"
        self._schema_data = {}
    
    def _get_parameters(self) -> Dict[str, Any]:
        if hasattr(self, '_schema_data') and self._schema_data:
            return self._schema_data.get("parameters", {})
        return {}
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

class ToolRegistry:
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[BaseTool]:
        return list(self._tools.values())
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [tool.get_schema() for tool in self._tools.values()]

tool_registry = ToolRegistry()

def register_tool(tool: BaseTool):
    tool_registry.register(tool)
