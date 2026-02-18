#!/usr/bin/env python3
"""
Simple test to verify LiteLLM proxy routing
"""
import requests
import json
import sys

def test_route(model_name, message_content):
    """Test routing for a specific model"""
    url = "http://localhost:4000/v1/chat/completions"
    headers = {
        "Authorization": "Bearer sk-vibe-master-123",
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
    # Test 1: Simple message to chat-auto (should route to mini)
    test_route("chat-auto", "hi")
    
    # Test 2: Complex message to chat-auto (should route to standard)
    test_route("chat-auto", "Please analyze the architectural patterns in this complex distributed system")
    
    # Test 3: Simple message to claude-auto
    test_route("claude-auto", "ls")
    
    # Test 4: Complex message to codex-auto
    test_route("codex-auto", "Implement a recursive backtracking algorithm for solving N-Queens problem")
