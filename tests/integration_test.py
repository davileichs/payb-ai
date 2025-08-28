#!/usr/bin/env python3
"""
Integration Test for Slack Bot AI Chat
This test runs through Docker and verifies all functionality:
1. Check if LLM is answering
2. Test provider switching (OpenAI/Ollama)
3. Test weather functionality
4. Test agent name recognition
"""

import os
import sys
import json
import time
import requests
import subprocess
from typing import Dict, Any, Optional

class IntegrationTest:
    def __init__(self):
        self.base_url = self._get_base_url()
        self.test_user_id = "integration_test_user"
        self.test_channel_id = "integration_test_channel"
        self.auth_token = self._get_auth_token()
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        self.test_results = []
        
    def _get_base_url(self) -> str:
        """Get base URL from environment or .env file"""
        # Try environment variable first
        port = os.getenv("PORT", "8000")
        host = os.getenv("HOST", "localhost")
        
        # Try to read from .env file if it exists
        env_file = ".env"
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("PORT="):
                            port = line.split("=", 1)[1]
                        elif line.startswith("HOST="):
                            host = line.split("=", 1)[1]
            except Exception as e:
                print(f"Warning: Could not read .env file: {e}")
        
        # Clean up host (remove protocol if present)
        if host.startswith("http://"):
            host = host[7:]
        elif host.startswith("https://"):
            host = host[5:]
        
        return f"http://{host}:{port}"
    
    def _get_auth_token(self) -> str:
        """Get auth token from environment or .env file"""
        # Try environment variable first
        token = os.getenv("JWT_SECRET_KEY")
        
        # Try to read from .env file if it exists
        if not token and os.path.exists(".env"):
            try:
                with open(".env", 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("JWT_SECRET_KEY="):
                            token = line.split("=", 1)[1]
                            break
            except Exception as e:
                print(f"Warning: Could not read JWT_SECRET_KEY from .env: {e}")
        
        if not token:
            token = "test-token"  # Fallback for testing
        
        return token
    
    def log_test(self, test_name: str, success: bool, message: str, details: Optional[Dict] = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        if details:
            print(f"    Details: {json.dumps(details, indent=2)}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        })
    
    def check_health(self) -> bool:
        """Check if the application is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Application is healthy", data)
                return True
            else:
                self.log_test("Health Check", False, f"Health check failed with status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Health check failed: {str(e)}")
            return False
    
    def test_llm_response(self, provider: str = None) -> bool:
        """Test if LLM is responding"""
        try:
            payload = {
                "message": "Hello, can you respond with just 'Hello'?",
                "user_id": self.test_user_id,
                "channel_id": self.test_channel_id,
                "use_tools": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/ai/chat",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "").lower()
                used_provider = data.get("provider", "unknown")
                
                if "hello" in response_text:
                    self.log_test(
                        f"LLM Response ({used_provider})", 
                        True, 
                        f"LLM responded correctly", 
                        {"response": data.get("response"), "provider": used_provider}
                    )
                    return True
                else:
                    self.log_test(
                        f"LLM Response ({used_provider})", 
                        False, 
                        f"LLM response didn't contain 'hello': {data.get('response')}"
                    )
                    return False
            else:
                self.log_test("LLM Response", False, f"Chat API failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("LLM Response", False, f"Chat API failed: {str(e)}")
            return False
    
    def switch_provider(self, provider: str) -> bool:
        """Switch AI provider"""
        try:
            payload = {
                "channel_id": self.test_channel_id,
                "provider": provider
            }
            
            response = requests.post(
                f"{self.base_url}/api/ai/provider/switch",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test(
                        f"Provider Switch to {provider}", 
                        True, 
                        f"Successfully switched to {provider}",
                        {"current_provider": data.get("current_provider")}
                    )
                    return True
                else:
                    self.log_test(f"Provider Switch to {provider}", False, data.get("message", "Switch failed"))
                    return False
            else:
                self.log_test(f"Provider Switch to {provider}", False, f"Switch API failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test(f"Provider Switch to {provider}", False, f"Switch API failed: {str(e)}")
            return False
    
    def test_weather_functionality(self, provider: str) -> bool:
        """Test weather functionality"""
        try:
            payload = {
                "message": "What's the weather like in Frankfurt?",
                "user_id": self.test_user_id,
                "channel_id": self.test_channel_id,
                "use_tools": True
            }
            
            response = requests.post(
                f"{self.base_url}/api/ai/chat",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "").lower()
                used_provider = data.get("provider", "unknown")
                
                # Check if response contains weather-related information
                weather_keywords = ["weather", "temperature", "frankfurt", "celsius", "fahrenheit", "degrees"]
                has_weather_info = any(keyword in response_text for keyword in weather_keywords)
                
                if has_weather_info:
                    self.log_test(
                        f"Weather Test ({used_provider})", 
                        True, 
                        f"Weather functionality working",
                        {"response": data.get("response"), "provider": used_provider}
                    )
                    return True
                else:
                    self.log_test(
                        f"Weather Test ({used_provider})", 
                        False, 
                        f"Weather response doesn't contain weather info: {data.get('response')}"
                    )
                    return False
            else:
                self.log_test(f"Weather Test ({provider})", False, f"Weather API failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test(f"Weather Test ({provider})", False, f"Weather API failed: {str(e)}")
            return False
    
    def test_agent_name_recognition(self, provider: str) -> bool:
        """Test if the agent recognizes its name as payb.ai"""
        try:
            payload = {
                "message": "What is your name?",
                "user_id": self.test_user_id,
                "channel_id": self.test_channel_id,
                "use_tools": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/ai/chat",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "").lower()
                used_provider = data.get("provider", "unknown")
                
                # Check if response contains the agent name
                name_variations = ["payb.ai", "payb", "paybai", "payb_ai"]
                has_correct_name = any(name in response_text for name in name_variations)
                
                if has_correct_name:
                    self.log_test(
                        f"Agent Name Test ({used_provider})", 
                        True, 
                        f"Agent correctly identifies as payb.ai",
                        {"response": data.get("response"), "provider": used_provider}
                    )
                    return True
                else:
                    self.log_test(
                        f"Agent Name Test ({used_provider})", 
                        False, 
                        f"Agent doesn't identify as payb.ai: {data.get('response')}"
                    )
                    return False
            else:
                self.log_test(f"Agent Name Test ({provider})", False, f"Name API failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test(f"Agent Name Test ({provider})", False, f"Name API failed: {str(e)}")
            return False
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get current provider status"""
        try:
            response = requests.get(
                f"{self.base_url}/api/ai/provider/status/{self.test_channel_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status API failed with status {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Status API failed: {str(e)}"}
    
    def run_all_tests(self) -> bool:
        """Run all integration tests"""
        print("🚀 Starting Integration Tests for Slack Bot AI Chat")
        print(f"📍 Base URL: {self.base_url}")
        print(f"🔑 Auth Token: {self.auth_token[:10]}..." if len(self.auth_token) > 10 else f"🔑 Auth Token: {self.auth_token}")
        print("=" * 60)
        
        # Step 1: Health Check
        if not self.check_health():
            print("❌ Health check failed. Aborting tests.")
            return False
        
        # Step 2: Test initial LLM response
        print("\n📝 Step 1: Testing initial LLM response...")
        if not self.test_llm_response():
            print("❌ Initial LLM response failed. Aborting tests.")
            return False
        
        # Step 3: Test provider switching and responses
        print("\n🔄 Step 2: Testing provider switching...")
        
        # Get current provider
        status = self.get_provider_status()
        current_provider = status.get("current_provider", "unknown")
        print(f"Current provider: {current_provider}")
        
        # Test both providers
        providers_to_test = ["openai", "ollama"]
        if current_provider in providers_to_test:
            providers_to_test.remove(current_provider)
        
        # Test current provider first
        print(f"\n🧪 Testing current provider: {current_provider}")
        self.test_llm_response(current_provider)
        self.test_weather_functionality(current_provider)
        self.test_agent_name_recognition(current_provider)
        
        # Test switching to other provider
        for provider in providers_to_test:
            print(f"\n🔄 Switching to provider: {provider}")
            if self.switch_provider(provider):
                time.sleep(2)  # Wait for provider switch to take effect
                
                print(f"\n🧪 Testing provider: {provider}")
                self.test_llm_response(provider)
                self.test_weather_functionality(provider)
                self.test_agent_name_recognition(provider)
        
        # Step 4: Test reload functionality
        print("\n🔄 Step 3: Testing reload functionality...")
        try:
            response = requests.post(
                f"{self.base_url}/api/ai/reload/agents",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Agents Reload", True, "Agents configuration reloaded successfully")
                else:
                    self.log_test("Agents Reload", False, "Agents reload failed")
            else:
                self.log_test("Agents Reload", False, f"Reload API failed with status {response.status_code}")
                
        except Exception as e:
            self.log_test("Agents Reload", False, f"Reload API failed: {str(e)}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        success = failed_tests == 0
        print(f"\n{'🎉 ALL TESTS PASSED!' if success else '💥 SOME TESTS FAILED!'}")
        
        return success

def main():
    """Main function to run integration tests"""
    test = IntegrationTest()
    success = test.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
