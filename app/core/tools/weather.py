import asyncio
from typing import Dict, Any
from app.core.tools.base import BaseTool, ToolResult, register_tool

class WeatherTool(BaseTool):
    
    async def execute(self, **kwargs) -> ToolResult:
        try:
            location = kwargs.get("location", "Unknown")
            units = kwargs.get("units", "metric")
            
            # Simulate API call delay
            await asyncio.sleep(0.1)
            
            # Mock weather data (in a real implementation, you'd call a weather API)
            weather_data = {
                "location": location,
                "temperature": 22 if units == "metric" else 72,
                "units": units,
                "condition": "Partly cloudy",
                "humidity": 65,
                "wind_speed": 15
            }
            
            return ToolResult(
                success=True,
                data=weather_data,
                metadata={
                    "tool_name": "WeatherTool",
                    "execution_time_ms": 100
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool_name": "WeatherTool"}
            )

# Register the tool automatically
register_tool(WeatherTool())
