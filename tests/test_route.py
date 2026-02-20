#!/usr/bin/env python3
"""
Comprehensive Test Suite for LiteLLM Virtual Model Routing
Tests the intelligent router plugin with various scenarios
"""
import os
import sys
import time
import json
import requests
import traceback
from typing import Dict, Any, Optional

# Configuration from environment variables
PROXY_URL = os.environ.get('LITELLM_BASE_URL', 'http://localhost:4000')
API_KEY = os.environ.get('LITELLM_MASTER_KEY', 'sk-litellm-master-key-12345678')

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ {text}{Colors.RESET}")

def test_health() -> bool:
    """Test if proxy is healthy"""
    print_header("Health Check")
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        print_info("Checking proxy health (this may take 30-45 seconds)...")
        response = requests.get(f"{PROXY_URL}/health", headers=headers, timeout=45)
        if response.status_code == 200:
            print_success(f"Proxy is healthy at {PROXY_URL}")
            return True
        else:
            print_error(f"Health check returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def list_models() -> Optional[Dict]:
    """List available models"""
    print_header("Available Models")
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.get(f"{PROXY_URL}/v1/models", headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get('data', [])
            print_success(f"Found {len(models)} models")
            for model in models[:10]:
                print(f"  - {model.get('id', 'unknown')}")
            return data
        else:
            print_error(f"Failed to list models: {response.status_code}")
            return None
    except Exception as e:
        print_error(f"Error listing models: {e}")
        return None

def test_route(
    model_name: str, 
    message: str, 
    expected_route: Optional[str] = None,
    description: str = ""
) -> bool:
    """
    Test a single routing scenario
    
    Args:
        model_name: Virtual model to test
        message: User message content
        expected_route: Expected physical model (for validation)
        description: Test description
    
    Returns:
        True if test passes, False otherwise
    """
    print_header(f"Test: {description or model_name}")
    print(f"Virtual Model: {Colors.BOLD}{model_name}{Colors.RESET}")
    print(f"Message: {message[:50]}{'...' if len(message) > 50 else ''}")
    if expected_route:
        print(f"Expected Route: {Colors.YELLOW}{expected_route}{Colors.RESET}")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": message}
        ],
        "max_tokens": 10,
        "temperature": 0.1
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{PROXY_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        duration = time.time() - start_time
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Duration: {duration:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            returned_model = data.get('model', 'unknown')
            usage = data.get('usage', {})
            
            print_success(f"Request succeeded")
            print(f"Returned Model: {Colors.BOLD}{returned_model}{Colors.RESET}")
            print(f"Tokens Used: {usage.get('total_tokens', 'N/A')}")
            
            if expected_route:
                if returned_model == expected_route or returned_model == model_name:
                    print_success("Routing validation passed")
                    return True
                else:
                    print_error(f"Routing mismatch! Expected: {expected_route}, Got: {returned_model}")
                    return False
            return True
            
        elif response.status_code == 400:
            print_error(f"Bad request")
            print(f"Response: {response.text[:200]}")
            return False
            
        elif response.status_code == 401:
            print_error(f"Unauthorized - check API key")
            return False
            
        else:
            print_error(f"Request failed with status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.Timeout:
        print_error(f"Request timed out after 30s")
        return False
    except Exception as e:
        print_error(f"Request failed: {e}")
        traceback.print_exc()
        return False

def run_test_suite():
    """Run complete test suite"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║          LiteLLM Virtual Model Router Test Suite             ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    print(f"\nConfiguration:")
    print(f"  Proxy URL: {Colors.BOLD}{PROXY_URL}{Colors.RESET}")
    print(f"  API Key: {Colors.BOLD}{API_KEY[:20]}...{Colors.RESET}")
    
    results = []
    
    # Test 1: Health check
    if not test_health():
        print_error("Proxy is not healthy. Aborting tests.")
        return
    
    # Test 2: List models
    list_models()
    
    # Test 3-8: Routing scenarios
    test_cases = [
        {
            "model": "auto-chat",
            "message": "hi",
            "expected": "auto-chat",
            "description": "auto-chat: Simple greeting"
        },
        {
            "model": "auto-chat-mini",
            "message": "What is 2+2?",
            "expected": "auto-chat-mini",
            "description": "auto-chat-mini: Simple math"
        },
        {
            "model": "auto-claude",
            "message": "Explain quantum computing",
            "expected": "auto-claude",
            "description": "auto-claude: Complex explanation"
        },
        {
            "model": "auto-claude-mini",
            "message": "Say hello",
            "expected": "auto-claude-mini",
            "description": "auto-claude-mini: Simple task"
        },
        {
            "model": "auto-codex",
            "message": "Write a Python function to reverse a string",
            "expected": "auto-codex",
            "description": "auto-codex: Code generation"
        },
        {
            "model": "auto-codex-mini",
            "message": "Print hello world in Python",
            "expected": "auto-codex-mini",
            "description": "auto-codex-mini: Simple code"
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{Colors.BOLD}[Test {i}/{len(test_cases)}]{Colors.RESET}")
        result = test_route(
            model_name=test_case["model"],
            message=test_case["message"],
            expected_route=test_case.get("expected"),
            description=test_case["description"]
        )
        results.append((test_case["description"], result))
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for desc, result in results:
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  [{status}] {desc}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed! 🎉{Colors.RESET}\n")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Some tests failed{Colors.RESET}\n")

if __name__ == "__main__":
    try:
        run_test_suite()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.RESET}")
        sys.exit(130)
