#!/usr/bin/env python3
"""
Test script to verify provider switching functionality.
"""

import requests
import json
import time

def get_api_key():
    # Try to read from .env file first
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('JWT_SECRET_KEY='):
                    return line.split('=', 1)[1].strip().split('#')[0].strip()
    except:
        pass
    
    # Fallback to hardcoded test key for development
    return "test-super-secret-jwt-key-for-development-only"

def send_chat_message(api_key, message, user_id="test_user", channel_id="test_channel"):
    url = "http://localhost:8000/api/ai/chat"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "message": message,
        "user_id": user_id,
        "channel_id": channel_id,
        "use_tools": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def main():
    api_key = get_api_key()
    if not api_key:
        print("❌ No API key found")
        return
    
    print("🧪 Testing Provider Switching Functionality")
    print("=" * 50)
    
    # Test 0: Check available providers first
    print("\n📝 Step 0: Check available providers")
    providers_response = send_chat_message(api_key, "Please list all available AI providers using the provider handle tool")
    
    if providers_response:
        print(f"💬 Providers response: {providers_response.get('response', 'No response')[:200]}...")
    
    # Test 1: Check initial provider
    print("\n📝 Step 1: Check initial provider")
    response1 = send_chat_message(api_key, "Hello! What AI provider are you using?")
    
    if response1:
        print(f"✅ Initial Provider: {response1.get('provider', 'unknown')}")
        print(f"✅ Initial Model: {response1.get('model', 'unknown')}")
        print(f"💬 Response: {response1.get('response', 'No response')[:100]}...")
        initial_provider = response1.get('provider')
        
        # Additional check: verify this matches .env setting
        print(f"\n🔍 Configuration Check:")
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('AI_PROVIDER='):
                        configured_provider = line.split('=', 1)[1].strip().split('#')[0].strip()
                        print(f"   📋 Configured in .env: {configured_provider}")
                        print(f"   🎯 Actually using: {initial_provider}")
                        if configured_provider != initial_provider:
                            print(f"   ⚠️  MISMATCH: Expected {configured_provider}, got {initial_provider}")
                        else:
                            print(f"   ✅ Configuration matches!")
                        break
        except Exception as e:
            print(f"   ❌ Could not read .env: {e}")
    else:
        print("❌ Failed to get initial response")
        return
    
    # Test 2: Request provider switch to Ollama
    print(f"\n📝 Step 2: Request switch to Ollama")
    switch_message = "Please switch to ollama provider using the provider handle tool"
    response2 = send_chat_message(api_key, switch_message)
    
    if response2:
        print(f"✅ Provider after switch request: {response2.get('provider', 'unknown')}")
        print(f"✅ Model after switch request: {response2.get('model', 'unknown')}")
        print(f"💬 Response: {response2.get('response', 'No response')[:100]}...")
        
        # Check if provider changed
        new_provider = response2.get('provider')
        if new_provider != initial_provider:
            print(f"🎉 SUCCESS: Provider switched from {initial_provider} to {new_provider}")
        else:
            print(f"⚠️  Provider still: {new_provider}")
    else:
        print("❌ Failed to get switch response")
        return
    
    # Test 3: Send another message to confirm the switch persisted
    print(f"\n📝 Step 3: Confirm provider switch persisted")
    response3 = send_chat_message(api_key, "What provider are you using now?")
    
    if response3:
        print(f"✅ Provider in follow-up: {response3.get('provider', 'unknown')}")
        print(f"✅ Model in follow-up: {response3.get('model', 'unknown')}")
        print(f"💬 Response: {response3.get('response', 'No response')[:100]}...")
        
        final_provider = response3.get('provider')
        if final_provider == 'ollama':
            print("🎉 SUCCESS: Provider switching is working correctly!")
        else:
            print(f"❌ FAILED: Expected 'ollama', got '{final_provider}'")
    else:
        print("❌ Failed to get confirmation response")
    
    # Test 4: Try switching back to OpenAI
    print(f"\n📝 Step 4: Switch back to OpenAI")
    switch_back_message = "Please switch back to openai provider"
    response4 = send_chat_message(api_key, switch_back_message)
    
    if response4:
        print(f"✅ Provider after switch back: {response4.get('provider', 'unknown')}")
        print(f"✅ Model after switch back: {response4.get('model', 'unknown')}")
        print(f"💬 Response: {response4.get('response', 'No response')[:100]}...")
        
        back_provider = response4.get('provider')
        if back_provider == 'openai':
            print("🎉 SUCCESS: Switch back to OpenAI working!")
        else:
            print(f"⚠️  Provider is: {back_provider}")
    else:
        print("❌ Failed to get switch back response")
    
    print("\n" + "=" * 50)
    print("🏁 Provider Switching Test Complete!")
    print("\n💡 Summary:")
    print("- Provider switching should work through natural language")
    print("- The AI should use the ProviderHandle tool to switch providers")
    print("- The JSON response should show the new provider")
    print("- Subsequent messages should use the new provider")

if __name__ == "__main__":
    main()

