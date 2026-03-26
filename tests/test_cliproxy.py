#!/usr/bin/env python3
"""
CLIProxyAPI Direct Test - Tests CLIProxyAPI 8317 port directly (bypassing LiteLLM)

This script validates:
- CLIProxyAPI 8317 port connectivity
- API key authentication (CHAT_AUTO_API_KEY)
- Model routing for auto-chat and auto-chat-mini
- Returns actual model name and response time
"""

import os
import sys
import time
import requests
from typing import Optional, Dict, Any

# Load environment variables from tests/.env
ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

# Configuration
CLIPROXY_BASE_URL = os.environ.get('CLIPROXY_BASE_URL', 'http://localhost:8317')
CHAT_AUTO_API_KEY = os.environ.get('CHAT_AUTO_API_KEY', 'sk-auto-chat-proxy-key')
TIMEOUT = 30

# Models to test (CLIProxyAPI backend models, not LiteLLM virtual models)
MODELS = [
    "claude-sonnet-4-6",    # L1: CLIProxyAPI (auto-chat backend)
    "gemini-2.5-flash",     # L1: CLIProxyAPI (auto-chat-mini backend)
]


def infer_route_from_model(model_name: str) -> str:
    """
    Infer the route layer based on the returned model name.

    CLIProxyAPI (L1) models:
    - claude-sonnet-4-6, gemini-2.5-flash

    New API (L2) models:
    - gpt-5, gpt-5-mini

    Volces Ark (L3) models:
    - glm-4.7, ark-code-latest
    """
    l1_models = ["claude-sonnet-4-6", "gemini-2.5-flash", "claude-sonnet-4-5", "claude-haiku-4-5"]
    l2_models = ["gpt-5", "gpt-5-mini", "gpt-5.2-codex", "gpt-5.1-codex-mini"]
    l3_models = ["glm-4.7", "ark-code-latest"]

    # Normalize model name
    normalized = model_name.lower().replace("openai/", "").replace("anthropic/", "")

    for l1_model in l1_models:
        if l1_model.lower() in normalized or normalized in l1_model.lower():
            return "L1: CLIProxyAPI (:8317)"

    for l2_model in l2_models:
        if l2_model.lower() in normalized or normalized in l2_model.lower():
            return "L2: New API (:3000)"

    for l3_model in l3_models:
        if l3_model.lower() in normalized or normalized in l3_model.lower():
            return "L3: Volces Ark"

    return "Unknown Route"


def test_cliproxy_model(model_name: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Test a single model against CLIProxyAPI directly.

    Args:
        model_name: The virtual model name to test
        verbose: Whether to print detailed output

    Returns:
        Dictionary with test results
    """
    url = f"{CLIPROXY_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {CHAT_AUTO_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Say hi briefly"}],
        "max_tokens": 20  # Minimum 16 required for some models
    }

    result = {
        "model": model_name,
        "success": False,
        "returned_model": "unknown",
        "route": "N/A",
        "response_time_ms": 0,
        "status_code": 0,
        "error": None
    }

    start_time = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["response_time_ms"] = elapsed_ms
        result["status_code"] = response.status_code

        if response.status_code == 200:
            data = response.json()
            returned_model = data.get('model', 'unknown')
            result["returned_model"] = returned_model
            result["route"] = infer_route_from_model(returned_model)
            result["success"] = True

            if verbose:
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')[:50]
                print(f"  Response: {content}...")
        else:
            result["error"] = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                result["error"] += f" - {error_data.get('error', {}).get('message', 'Unknown error')}"
            except:
                pass

    except requests.exceptions.Timeout:
        result["error"] = f"Timeout ({TIMEOUT}s)"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"Connection Error: {str(e)}"
    except Exception as e:
        result["error"] = f"Error: {str(e)}"

    return result


def print_result(result: Dict[str, Any], verbose: bool = True) -> None:
    """Print test result in formatted output."""
    status = "✅" if result["success"] else "❌"
    model_display = result["returned_model"] if result["success"] else result["error"]
    route_info = f" [{result['route']}]" if result["success"] else ""
    time_info = f" ({result['response_time_ms']}ms)" if result["success"] else ""

    print(f"{status} {result['model']:20s} → {model_display:25s}{route_info}{time_info}")


def run_tests(verbose: bool = True) -> Dict[str, bool]:
    """
    Run all CLIProxyAPI tests.

    Returns:
        Dictionary mapping model names to success/failure
    """
    print("=" * 70)
    print("CLIProxyAPI 直连测试 (端口 8317)")
    print("=" * 70)
    print(f"Base URL: {CLIPROXY_BASE_URL}")
    print(f"API Key: {CHAT_AUTO_API_KEY[:20]}...")
    print(f"Timeout: {TIMEOUT}s")
    print("=" * 70)
    print("\n注意：CLIProxyAPI 使用实际后端模型名称，而非 LiteLLM 虚拟模型名称")
    print("  - claude-sonnet-4-6  (auto-chat 的 L1 后端)")
    print("  - gemini-2.5-flash   (auto-chat-mini 的 L1 后端)")
    print("=" * 70)

    results = {}

    for model_name in MODELS:
        if verbose:
            print(f"\nTesting: {model_name}")

        result = test_cliproxy_model(model_name, verbose)
        results[model_name] = result["success"]

        print_result(result, verbose)

    # Summary
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"通过：{passed}/{total} ({passed*100//total if total > 0 else 0}%)")

    if passed == total:
        print("\n🎉 所有 CLIProxyAPI 测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        for model, success in results.items():
            if not success:
                print(f"  - {model}")

    return results


if __name__ == "__main__":
    verbose = "--quiet" not in sys.argv
    results = run_tests(verbose)

    # Exit with error code if any test failed
    if not all(results.values()):
        sys.exit(1)
