import asyncio
import httpx
from typing import Dict, Any
from app.core.tools.base import BaseTool, ToolResult, register_tool
from app.config import get_settings

class WeatherTool(BaseTool):
    
    def __init__(self):
        super().__init__()
        self.settings = get_settings()
    
    async def execute(self, **kwargs) -> ToolResult:
        location = kwargs.get("location")
        units = kwargs.get("units", "metric")
        
        try:
            if not self.settings.open_weather_key:
                return ToolResult(
                    success=False,
                    error="OPEN_WEATHER_KEY not configured"
                )
            
            # Use geocoding API to get coordinates for the location
            geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={self.settings.open_weather_key}"
            
            async with httpx.AsyncClient() as client:
                geocode_response = await client.get(geocode_url)
                geocode_data = geocode_response.json()
                
                if not geocode_data:
                    return ToolResult(
                        success=False,
                        error=f"Location '{location}' not found"
                    )
                
                lat = geocode_data[0]["lat"]
                lon = geocode_data[0]["lon"]
                
                # Get weather data
                weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.settings.open_weather_key}&units={units}"
                weather_response = await client.get(weather_url)
                weather_data = weather_response.json()
                
                if weather_response.status_code != 200:
                    return ToolResult(
                        success=False,
                        error=f"Weather API error: {weather_data.get('message', 'Unknown error')}"
                    )
                
                return ToolResult(
                    success=True,
                    data={
                        "location": location,
                        "temperature": weather_data["main"]["temp"],
                        "description": weather_data["weather"][0]["description"],
                        "humidity": weather_data["main"]["humidity"],
                        "wind_speed": weather_data["wind"]["speed"],
                        "units": units
                    }
                )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Weather lookup error: {str(e)}"
            )

# Register the tool automatically
register_tool(WeatherTool())
