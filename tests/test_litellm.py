#!/usr/bin/env python3
"""
LiteLLM Routing Test - Tests LiteLLM 4000 port with routing information

This script validates:
- LiteLLM 4000 port connectivity
- All 6 virtual models routing
- Returns actual model name and route path (L1/L2/L3)
- Detects fallback triggering based on returned model

Architecture:
  L1: CLIProxyAPI (:8317) - OAuth free tier
  L2: New API (:3000) - Self-hosted forwarder
  L3: Volces Ark - Commercial paid fallback
"""

import os
import sys
import time
import requests
from typing import Optional, Dict, Any, List, Tuple

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
LITELLM_BASE_URL = os.environ.get('LITELLM_BASE_URL', 'http://localhost:4000')
LITELLM_MASTER_KEY = os.environ.get('LITELLM_MASTER_KEY', 'sk-litellm-master-key')
TIMEOUT = 60  # Longer timeout for LiteLLM as it may try multiple fallbacks

# All 6 virtual models
MODELS = [
    "auto-chat",
    "auto-chat-mini",
    "auto-claude",
    "auto-claude-mini",
    "auto-codex",
    "auto-codex-mini",
]

# Expected primary route for each model (when no fallback)
EXPECTED_PRIMARY_ROUTE = {
    "auto-chat": "L1: CLIProxyAPI (:8317)",
    "auto-chat-mini": "L1: CLIProxyAPI (:8317)",
    "auto-claude": "L1: CLIProxyAPI (:8317)",  # Now uses CLIProxyAPI with claude-sonnet-4-6
    "auto-claude-mini": "L2: New API (:3000)",
    "auto-codex": "L2: New API (:3000)",
    "auto-codex-mini": "L2: New API (:3000)",
}


def infer_route_from_model(model_name: str, requested_model: str) -> Tuple[str, bool]:
    """
    Infer the route layer and whether fallback was triggered.

    Note: When LiteLLM returns the virtual model name (e.g., 'auto-chat')
    instead of the backend model, we report the expected primary route.
    Fallback detection requires analyzing the actual backend model name.

    Returns:
        Tuple of (route_string, fallback_triggered)
    """
    # Normalize model name
    normalized = model_name.lower().replace("openai/", "").replace("anthropic/", "")

    # Check if response contains virtual model name (passthrough mode)
    virtual_models = ["auto-chat", "auto-chat-mini", "auto-claude", "auto-claude-mini", "auto-codex", "auto-codex-mini"]
    is_passthrough = any(vm in normalized for vm in virtual_models)

    # L1: CLIProxyAPI models (only for auto-chat and auto-chat-mini)
    l1_models = {
        "claude-sonnet-4-6", "claude-sonnet-4-5",
        "gemini-2.5-flash", "claude-haiku-4-5"
    }

    # L2: New API models
    l2_models = {
        "gpt-5", "gpt-5-mini",
        "gpt-5.2-codex", "gpt-5.1-codex-mini",
        "claude-sonnet-4-5", "claude-haiku-4-5"  # Also via New API
    }

    # L3: Volces Ark models
    l3_models = {"glm-4.7", "ark-code-latest"}

    # If passthrough mode (virtual model name returned), use expected route
    if is_passthrough:
        expected = EXPECTED_PRIMARY_ROUTE.get(requested_model, "Unknown Route")
        return (expected, False)  # Can't detect fallback in passthrough mode

    # Check L1
    for l1_model in l1_models:
        if l1_model in normalized or normalized in l1_model:
            # For auto-claude/auto-claude-mini, this would be L2, not L1
            if requested_model in ["auto-chat", "auto-chat-mini"]:
                return ("L1: CLIProxyAPI (:8317)", False)
            else:
                return ("L2: New API (:3000)", False)

    # Check L2
    for l2_model in l2_models:
        if l2_model in normalized or normalized in l2_model:
            expected = EXPECTED_PRIMARY_ROUTE.get(requested_model, "")
            is_fallback = "L1" in expected  # If expected L1 but got L2, it's fallback
            return ("L2: New API (:3000)", is_fallback)

    # Check L3
    for l3_model in l3_models:
        if l3_model in normalized or normalized in l3_model:
            expected = EXPECTED_PRIMARY_ROUTE.get(requested_model, "")
            is_fallback = "L1" in expected or "L2" in expected  # If expected L1/L2 but got L3, it's fallback
            return ("L3: Volces Ark", is_fallback)

    return ("Unknown Route", False)


def test_litellm_model(model_name: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Test a single model against LiteLLM proxy.

    Args:
        model_name: The virtual model name to test
        verbose: Whether to print detailed output

    Returns:
        Dictionary with test results
    """
    url = f"{LITELLM_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {LITELLM_MASTER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Say hi briefly"}],
        "max_tokens": 20  # Minimum 16 required for some models (auto-codex)
    }

    result = {
        "model": model_name,
        "success": False,
        "returned_model": "unknown",
        "route": "N/A",
        "fallback_triggered": False,
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

            route, fallback = infer_route_from_model(returned_model, model_name)
            result["route"] = route
            result["fallback_triggered"] = fallback

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
    fallback_warning = " ⚠️ FALLBACK" if result.get("fallback_triggered") else ""
    time_info = f" ({result['response_time_ms']}ms)" if result["success"] else ""

    print(f"{status} {result['model']:20s} → {model_display:25s}{route_info}{fallback_warning}{time_info}")


def run_tests(verbose: bool = True) -> Dict[str, bool]:
    """
    Run all LiteLLM routing tests.

    Returns:
        Dictionary mapping model names to success/failure
    """
    print("=" * 75)
    print("LiteLLM 路由测试 (端口 4000)")
    print("=" * 75)
    print(f"Base URL: {LITELLM_BASE_URL}")
    print(f"API Key: {LITELLM_MASTER_KEY[:20]}...")
    print(f"Timeout: {TIMEOUT}s")
    print("=" * 75)
    print("\n路由层级说明:")
    print("  L1: CLIProxyAPI (:8317)  - OAuth 免费层 (auto-chat 专用)")
    print("  L2: New API (:3000)      - 自建转发层")
    print("  L3: Volces Ark           - 商业付费层 (最终降级)")
    print("=" * 75)

    results = {}

    for model_name in MODELS:
        if verbose:
            print(f"\n测试：{model_name}")
            expected = EXPECTED_PRIMARY_ROUTE.get(model_name, "Unknown")
            print(f"  预期路由：{expected}")

        result = test_litellm_model(model_name, verbose)
        results[model_name] = result["success"]

        print_result(result, verbose)

    # Summary
    print("\n" + "=" * 75)
    print("测试总结")
    print("=" * 75)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"通过：{passed}/{total} ({passed*100//total if total > 0 else 0}%)")

    # Count fallbacks
    fallback_count = 0
    for model_name in MODELS:
        if results.get(model_name):
            # Re-run to check fallback (in real scenario, we'd store the result)
            pass

    if passed == total:
        print("\n🎉 所有 LiteLLM 路由测试通过！")
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
