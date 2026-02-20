#!/usr/bin/env python3
"""
Simple test to verify LiteLLM proxy routing
"""
import os
import requests
import json
import sys

def test_route(model_name, message_content, api_key=None, base_url=None):
    """Test routing for a specific model"""
    # Get configuration from environment variables
    api_key = api_key or os.environ.get('LITELLM_MASTER_KEY', 'sk-litellm-master-key-12345678')
    base_url = base_url or os.environ.get('LITELLM_BASE_URL', 'http://localhost:4000')
    
    url = f"{base_url}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": message_content}
        ],
        "max_tokens": 10
    }
    
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"Message: {message_content}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return None

if __name__ == "__main__":
    # Test 1: Simple message to auto-chat (should route to mini)
    test_route("auto-chat", "hi")
    
    # Test 2: Complex message to auto-chat (should route to standard)
    test_route("auto-chat", "Please analyze the architectural patterns in this complex distributed system")
    
    # Test 3: Simple message to auto-claude
    test_route("auto-claude", "ls")
    
    # Test 4: Complex message to auto-codex
    test_route("auto-codex", "Implement a recursive backtracking algorithm for solving N-Queens problem")
