#!/usr/bin/env python3
"""
Fallback 层级检测测试脚本
测试每个虚拟模型的 actual fallback 层级，判断系统健康度

测试原理：
1. 发送请求到虚拟模型
2. 从返回的 model 字段和响应内容判断实际使用的后端
3. 统计每个模型的 fallback 层级分布
4. 评估系统健康状态

Fallback 策略 (4 层降级):
  auto-chat:       L1: gemini-3.1-pro-low → L2: gpt-5 → L3: glm-5 → L4: kimi-k2.5
  auto-chat-mini:  L1: gemini-2.5-flash → L2: gpt-5-mini → L3: glm-4.7 → L4: ark-code-latest
  auto-claude:     L1: claude-sonnet-4-6 → L2: claude-sonnet-4-5 → L3: glm-5 → L4: glm-4.7
  auto-claude-max: L1: claude-opus-4-6 → L2: claude-opus-4-5 → L3: glm-5 → L4: kimi-k2.5
  auto-claude-mini: L1: claude-haiku-4-5 → L2: claude-haiku-4-5 → L3: glm-4.7 → L4: ark-code-latest
  auto-codex:      L2: gpt-5.2-codex (仅 New API)
  auto-codex-mini: L2: gpt-5.1-codex-mini (仅 New API)
"""

import os
import sys
import json
import requests
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# 从 .env 文件加载配置
def load_env():
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

env = load_env()

API_KEY = os.environ.get('LITELLM_MASTER_KEY', env.get('LITELLM_MASTER_KEY', 'sk-xY93Zr8Bp1TEebwDCkDQqA'))
BASE_URL = os.environ.get('LITELLM_BASE_URL', 'http://localhost:4000')

# 7 个虚拟模型
MODELS = [
    "auto-chat",
    "auto-chat-mini",
    "auto-claude",
    "auto-claude-max",
    "auto-claude-mini",
    "auto-codex",
    "auto-codex-mini",
]

# 模型到后端的映射关系 (用于判断层级)
MODEL_LAYER_MAP = {
    # auto-chat 系列
    "gemini-3.1-pro-low": ("auto-chat", "L1"),
    "gemini-2.5-flash": ("auto-chat-mini", "L1"),
    "gpt-5": ("auto-chat", "L2"),
    "gpt-5-mini": ("auto-chat-mini", "L2"),
    "glm-5": ("auto-chat/auto-claude-max", "L3"),
    "glm-4.7": ("auto-chat-mini/auto-claude-mini", "L3/L4"),
    "kimi-k2.5": ("auto-chat/auto-claude-max", "L4"),
    "ark-code-latest": ("auto-chat-mini/auto-claude-mini", "L4"),
    # Claude 系列
    "claude-sonnet-4-6": ("auto-chat/auto-claude", "L1"),
    "claude-sonnet-4-5": ("auto-claude", "L2"),
    "claude-opus-4-6": ("auto-claude-max", "L1"),
    "claude-opus-4-5": ("auto-claude-max", "L2"),
    "claude-haiku-4-5": ("auto-claude-mini", "L1/L2"),
    # Codex 系列
    "gpt-5.2-codex": ("auto-codex", "L2"),
    "gpt-5.1-codex-mini": ("auto-codex-mini", "L2"),
}


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def detect_layer(model: str, response_model: str, content: str) -> str:
    """
    根据返回的模型名称和响应内容判断命中了哪一层

    Returns: L1, L2, L3, L4, 或 Unknown
    """
    # 转小写进行比较
    rm = response_model.lower()
    content_lower = content.lower()

    # L1: CLIProxyAPI (Antigravity OAuth)
    if "gemini-3.1-pro-low" in rm or "gemini-3.1" in rm:
        return "L1"
    if "gemini-2.5-flash" in rm:
        return "L1"
    if "claude-sonnet-4-6" in rm and model == "auto-claude":
        return "L1"
    if "claude-opus-4-6" in rm:
        return "L1"
    if "claude-haiku-4-5" in rm and model == "auto-claude-mini":
        return "L1"

    # L2: New API (自建转发)
    if "gpt-5" in rm and "codex" not in rm:
        return "L2"
    if "claude-sonnet-4-5" in rm:
        return "L2"
    if "claude-opus-4-5" in rm:
        return "L2"
    if "gpt-5.2-codex" in rm or "gpt-5.2" in rm:
        return "L2"
    if "gpt-5.1-codex-mini" in rm or "gpt-5.1" in rm:
        return "L2"

    # L3: Zhipu API (智谱付费)
    if "glm-5" in rm or "glm5" in rm:
        return "L3"
    if "glm-4.7" in rm or "glm4.7" in rm:
        return "L3"
    # 通过响应内容判断（GLM 模型会自报家门）
    if "glm" in content_lower and "z.ai" in content_lower:
        return "L3"

    # L4: Volces Ark (最终降级)
    if "kimi" in rm or "kimi-k2.5" in rm:
        return "L4"
    if "ark-code" in rm:
        return "L4"

    return "Unknown"


def test_model(model_name: str, timeout: int = 60) -> Tuple[bool, str, str, float]:
    """
    测试单个模型

    Returns: (success, response_model, layer, duration)
    """
    url = f"{BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 20
    }

    try:
        import time
        start = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        duration = time.time() - start

        if response.status_code == 200:
            data = response.json()
            response_model = data.get('model', 'unknown')
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            layer = detect_layer(model_name, response_model, content)
            return True, response_model, layer, duration
        else:
            error_msg = response.text[:100] if response.text else f"HTTP {response.status_code}"
            return False, error_msg, "N/A", 0
    except requests.Timeout:
        return False, "Timeout", "N/A", timeout
    except Exception as e:
        return False, str(e), "N/A", 0


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def print_result(success: bool, model: str, response_model: str, layer: str, duration: float):
    """打印单个测试结果"""
    status = f"{Colors.GREEN}✅{Colors.RESET}" if success else f"{Colors.RED}❌{Colors.RESET}"

    # 层级颜色
    layer_color = {
        "L1": Colors.GREEN,
        "L2": Colors.BLUE,
        "L3": Colors.YELLOW,
        "L4": Colors.RED,
        "Unknown": Colors.RESET,
        "N/A": Colors.RESET,
    }.get(layer, Colors.RESET)

    duration_str = f"{duration:.2f}s" if duration > 0 else "N/A"

    print(f"{status} {model:20s} → {response_model:25s} [{layer_color}{layer:4s}{Colors.RESET}] {duration_str:>8s}")


def run_fallback_test(iterations: int = 3) -> Dict:
    """
    运行 fallback 层级测试

    Args:
        iterations: 每个模型测试次数

    Returns: 测试结果统计
    """
    print_header("Fallback 层级检测测试")
    print(f"{Colors.CYAN}测试配置:{Colors.RESET}")
    print(f"  目标地址：{BASE_URL}")
    print(f"  API Key: {API_KEY[:20]}...")
    print(f"  迭代次数：{iterations}")
    print(f"  测试模型：{len(MODELS)} 个")
    print()

    results = defaultdict(lambda: {"layers": defaultdict(int), "success": 0, "failed": 0, "durations": []})

    for i in range(iterations):
        print(f"\n{Colors.BOLD}[迭代 {i+1}/{iterations}]{Colors.RESET}")
        print("-" * 70)

        for model in MODELS:
            success, response_model, layer, duration = test_model(model)
            print_result(success, model, response_model, layer, duration)

            if success:
                results[model]["success"] += 1
                results[model]["layers"][layer] += 1
                if duration > 0:
                    results[model]["durations"].append(duration)
            else:
                results[model]["failed"] += 1

    return results


def print_summary(results: Dict):
    """打印测试总结和健康度评估"""
    print_header("测试总结与健康度评估")

    print(f"{Colors.BOLD}{'模型':<20} {'成功率':<12} {'主要层级':<20} {'平均耗时':<12} {'健康度':<10}{Colors.RESET}")
    print("-" * 84)

    overall_health = "健康"
    issues = []

    for model in MODELS:
        r = results[model]
        total = r["success"] + r["failed"]
        success_rate = r["success"] / total * 100 if total > 0 else 0

        # 找出主要层级
        if r["layers"]:
            main_layer = max(r["layers"].items(), key=lambda x: x[1])[0]
        else:
            main_layer = "N/A"

        # 计算平均耗时
        avg_duration = sum(r["durations"]) / len(r["durations"]) if r["durations"] else 0

        # 评估健康度
        if success_rate >= 80 and main_layer in ["L1", "L2"]:
            health = f"{Colors.GREEN}✅ 健康{Colors.RESET}"
        elif success_rate >= 80 and main_layer in ["L3", "L4"]:
            health = f"{Colors.YELLOW}⚠️  降级{Colors.RESET}"
            issues.append(f"{model} 频繁降级到 L3/L4")
        else:
            health = f"{Colors.RED}❌ 异常{Colors.RESET}"
            issues.append(f"{model} 成功率低 ({success_rate:.0f}%)")
            overall_health = "异常"

        layer_str = f"{main_layer}"
        if main_layer == "Unknown":
            layer_str = "Unknown"

        print(f"{model:<20} {success_rate:>5.0f}%        {layer_str:<20} {avg_duration:>6.2f}s       {health}")

    print()
    print("-" * 84)
    print(f"\n{Colors.BOLD}整体健康度：{overall_health}{Colors.RESET}\n")

    if issues:
        print(f"{Colors.YELLOW}⚠️  发现的问题:{Colors.RESET}")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"{Colors.GREEN}✅ 所有模型运行正常!{Colors.RESET}")

    print()


def main():
    # 支持命令行参数
    iterations = 1
    if len(sys.argv) > 1:
        try:
            iterations = int(sys.argv[1])
        except ValueError:
            print(f"用法：python3 {sys.argv[0]} [迭代次数]")
            print("示例：python3 test_fallback_layers.py 3")
            sys.exit(1)

    results = run_fallback_test(iterations)
    print_summary(results)

    # 写入测试结果到文件
    output_file = os.path.join(os.path.dirname(__file__), 'fallback_test_results.json')
    with open(output_file, 'w') as f:
        # 转换 defaultdict 为普通 dict 以便 JSON 序列化
        json_results = {}
        for model in MODELS:
            r = results[model]
            json_results[model] = {
                "success": r["success"],
                "failed": r["failed"],
                "layers": dict(r["layers"]),
                "avg_duration": sum(r["durations"]) / len(r["durations"]) if r["durations"] else 0,
            }
        json.dump(json_results, f, indent=2)

    print(f"测试结果已保存到：{output_file}")


if __name__ == "__main__":
    main()
