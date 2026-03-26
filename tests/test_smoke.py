#!/usr/bin/env python3
"""
Smoke Test - Continuous testing for all 6 models with stability analysis

This script validates:
- Model stability over multiple iterations (7 times per model)
- Response time statistics (min/max/avg)
- Route distribution across iterations
- Fallback trigger detection and counting

Test Parameters:
- All 6 virtual models
- 7 iterations per model
- 3 second interval between requests
"""

import os
import sys
import time
import requests
import statistics
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict

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
TIMEOUT = 60
ITERATIONS = 7
INTERVAL_SECONDS = 3

# All 6 virtual models
MODELS = [
    "auto-chat",
    "auto-chat-mini",
    "auto-claude",
    "auto-claude-mini",
    "auto-codex",
    "auto-codex-mini",
]

# Route inference mappings
L1_MODELS = {"claude-sonnet-4-6", "claude-sonnet-4-5", "gemini-2.5-flash", "claude-haiku-4-5"}
L2_MODELS = {"gpt-5", "gpt-5-mini", "gpt-5.2-codex", "gpt-5.1-codex-mini", "claude-sonnet-4-5", "claude-haiku-4-5"}
L3_MODELS = {"glm-4.7", "ark-code-latest"}


def infer_route(model_name: str, requested_model: str) -> str:
    """Infer the route layer based on returned model name."""
    normalized = model_name.lower().replace("openai/", "").replace("anthropic/", "")

    # Check if response contains virtual model name (passthrough mode)
    virtual_models = ["auto-chat", "auto-chat-mini", "auto-claude", "auto-claude-mini", "auto-codex", "auto-codex-mini"]
    is_passthrough = any(vm in normalized for vm in virtual_models)

    # Expected primary routes (for passthrough mode)
    primary_routes = {
        "auto-chat": "L1: CLIProxyAPI",
        "auto-chat-mini": "L1: CLIProxyAPI",
        "auto-claude": "L2: New API",
        "auto-claude-mini": "L2: New API",
        "auto-codex": "L2: New API",
        "auto-codex-mini": "L2: New API",
    }

    # If passthrough mode (virtual model name returned), use expected route
    if is_passthrough:
        return primary_routes.get(requested_model, "Unknown")

    # Check L1 (only for auto-chat/auto-chat-mini)
    if requested_model in ["auto-chat", "auto-chat-mini"]:
        for l1_model in L1_MODELS:
            if l1_model in normalized or normalized in l1_model:
                return "L1: CLIProxyAPI"

    # Check L2
    for l2_model in L2_MODELS:
        if l2_model in normalized or normalized in l2_model:
            return "L2: New API"

    # Check L3
    for l3_model in L3_MODELS:
        if l3_model in normalized or normalized in l3_model:
            return "L3: Volces Ark"

    return "Unknown"


def is_fallback(returned_model: str, requested_model: str) -> bool:
    """Detect if fallback was triggered based on route change."""
    route = infer_route(returned_model, requested_model)

    # Expected primary routes
    primary_routes = {
        "auto-chat": "L1",
        "auto-chat-mini": "L1",
        "auto-claude": "L2",
        "auto-claude-mini": "L2",
        "auto-codex": "L2",
        "auto-codex-mini": "L2",
    }

    expected = primary_routes.get(requested_model, "")
    if not expected:
        return False

    # If got L3 when expected L1 or L2, it's fallback
    if route == "L3: Volces Ark" and expected in ["L1", "L2"]:
        return True

    # If got L2 when expected L1, it's fallback
    if route == "L2: New API" and expected == "L1":
        return True

    return False


def test_model_iteration(model_name: str, iteration: int, verbose: bool = True) -> Dict[str, Any]:
    """
    Run a single test iteration for a model.

    Returns:
        Dictionary with iteration results
    """
    url = f"{LITELLM_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {LITELLM_MASTER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 20  # Minimum 16 required for some models (auto-codex)
    }

    result = {
        "iteration": iteration,
        "success": False,
        "returned_model": "unknown",
        "route": "N/A",
        "fallback": False,
        "response_time_ms": 0,
        "status_code": 0,
        "error": None,
        "timestamp": datetime.now().isoformat()
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
            result["route"] = infer_route(returned_model, model_name)
            result["fallback"] = is_fallback(returned_model, model_name)
            result["success"] = True

    except requests.exceptions.Timeout:
        result["error"] = f"Timeout ({TIMEOUT}s)"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"Connection Error"
    except Exception as e:
        result["error"] = f"Error"

    return result


def print_iteration_result(result: Dict[str, Any], model_name: str) -> None:
    """Print a single iteration result."""
    iteration = result["iteration"]
    status = "✅" if result["success"] else "❌"
    time_str = f"{result['response_time_ms']}ms" if result["success"] else "--"
    model_display = result["returned_model"] if result["success"] else "-"
    route = f"[{result['route']}]" if result["success"] else "[FAILED]"
    fallback_warning = " ⚠️ FALLBACK" if result.get("fallback") else ""

    print(f"[{iteration}/{ITERATIONS}] {status} {time_str:>8} → {model_display:22s} {route}{fallback_warning}")


def calculate_statistics(response_times: List[int]) -> Dict[str, Any]:
    """Calculate response time statistics."""
    if not response_times:
        return {"min": 0, "max": 0, "avg": 0, "median": 0}

    return {
        "min": min(response_times),
        "max": max(response_times),
        "avg": int(statistics.mean(response_times)),
        "median": int(statistics.median(response_times))
    }


def run_smoke_test(model_name: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Run smoke test for a single model (7 iterations).

    Returns:
        Dictionary with aggregated results
    """
    results = []
    response_times = []
    route_counts = defaultdict(int)
    fallback_count = 0
    success_count = 0

    for i in range(1, ITERATIONS + 1):
        result = test_model_iteration(model_name, i, verbose)
        results.append(result)

        if verbose:
            print_iteration_result(result, model_name)

        if result["success"]:
            success_count += 1
            response_times.append(result["response_time_ms"])
            route_counts[result["route"]] += 1
            if result["fallback"]:
                fallback_count += 1

        # Wait between iterations (except for the last one)
        if i < ITERATIONS:
            time.sleep(INTERVAL_SECONDS)

    # Calculate statistics
    stats = calculate_statistics(response_times)

    return {
        "model": model_name,
        "total_iterations": ITERATIONS,
        "success_count": success_count,
        "success_rate": success_count / ITERATIONS * 100,
        "response_times": stats,
        "route_distribution": dict(route_counts),
        "fallback_count": fallback_count,
        "all_results": results
    }


def print_smoke_summary(smoke_result: Dict[str, Any]) -> None:
    """Print smoke test summary for a model."""
    print("\n" + "-" * 70)
    print(f"统计总结 - {smoke_result['model']}")
    print("-" * 70)

    # Success rate
    success_rate = smoke_result["success_rate"]
    status_icon = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "❌"
    print(f"  {status_icon} 成功率：{smoke_result['success_count']}/{smoke_result['total_iterations']} ({success_rate:.1f}%)")

    # Response time stats
    rt = smoke_result["response_times"]
    if rt["avg"] > 0:
        print(f"  ⏱️  响应时间：{rt['min']}-{rt['max']}ms (avg: {rt['avg']}ms, median: {rt['median']}ms)")
    else:
        print(f"  ⏱️  响应时间：N/A (所有请求失败)")

    # Route distribution
    print(f"  🗺️  路由分布:")
    route_dist = smoke_result["route_distribution"]
    total_routed = sum(route_dist.values())
    for route, count in sorted(route_dist.items(), key=lambda x: -x[1]):
        pct = count / total_routed * 100 if total_routed > 0 else 0
        print(f"      {route}: {count} 次 ({pct:.1f}%)")

    # Fallback info
    if smoke_result["fallback_count"] > 0:
        print(f"  ⚠️  Fallback 触发：{smoke_result['fallback_count']} 次")
    else:
        print(f"  ✅ Fallback 触发：0 次")


def run_all_smoke_tests(verbose: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Run smoke tests for all 6 models.

    Returns:
        Dictionary mapping model names to their smoke test results
    """
    print("=" * 70)
    print("冒烟测试 - 所有 6 个虚拟模型")
    print("=" * 70)
    print(f"Base URL: {LITELLM_BASE_URL}")
    print(f"API Key: {LITELLM_MASTER_KEY[:20]}...")
    print(f"迭代次数：{ITERATIONS} 次/模型")
    print(f"间隔时间：{INTERVAL_SECONDS} 秒")
    print(f"总预计时间：{ITERATIONS * INTERVAL_SECONDS * len(MODELS) // 60} 分钟")
    print("=" * 70)

    all_results = {}
    overall_success = 0
    overall_total = 0

    for model_name in MODELS:
        print(f"\n{'='*70}")
        print(f"冒烟测试 - {model_name} ({ITERATIONS} 次迭代)")
        print(f"{'='*70}")

        result = run_smoke_test(model_name, verbose)
        all_results[model_name] = result

        print_smoke_summary(result)

        overall_success += result["success_count"]
        overall_total += result["total_iterations"]

    # Overall summary
    print("\n" + "=" * 70)
    print("总体测试总结")
    print("=" * 70)
    overall_rate = overall_success / overall_total * 100 if overall_total > 0 else 0
    print(f"总成功率：{overall_success}/{overall_total} ({overall_rate:.1f}%)")

    # Per-model summary table
    print("\n各模型表现:")
    print("-" * 70)
    print(f"{'模型':<22s} {'成功率':>12s} {'响应时间 (avg)':>18s} {'Fallback':>12s}")
    print("-" * 70)

    for model_name, result in all_results.items():
        success_str = f"{result['success_count']}/{result['total_iterations']} ({result['success_rate']:.0f}%)"
        rt = result["response_times"]
        rt_str = f"{rt['avg']}ms" if rt["avg"] > 0 else "N/A"
        fallback_str = str(result["fallback_count"])
        print(f"{model_name:<22s} {success_str:>12s} {rt_str:>18s} {fallback_str:>12s}")

    print("=" * 70)

    if overall_rate >= 80:
        print("\n🎉 冒烟测试通过！系统表现稳定。")
    elif overall_rate >= 50:
        print("\n⚠️  冒烟测试部分通过，建议检查不稳定的模型。")
    else:
        print("\n❌ 冒烟测试失败率较高，请检查系统配置。")

    return all_results


if __name__ == "__main__":
    verbose = "--quiet" not in sys.argv

    # Optional: override iterations via command line
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        ITERATIONS = int(sys.argv[1])
        print(f"使用自定义迭代次数：{ITERATIONS}")

    all_results = run_all_smoke_tests(verbose)

    # Exit with error code if overall success rate is too low
    overall_success = sum(r["success_count"] for r in all_results.values())
    overall_total = sum(r["total_iterations"] for r in all_results.values())
    overall_rate = overall_success / overall_total * 100 if overall_total > 0 else 0

    if overall_rate < 50:
        sys.exit(1)
