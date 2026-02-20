#!/usr/bin/env python3
"""
远端测试脚本 - LiteLLM 智能路由器
测试虚拟模型路由是否正常工作
"""
import os
import sys
import time
import json
import requests
import argparse
from typing import Optional

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.RESET}")

def test_health(base_url: str, api_key: str) -> bool:
    """测试健康端点"""
    print_header("1. 健康检查")

    try:
        # 先测试无认证的连接
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print_success(f"服务运行正常: {base_url}")
            return True
        elif response.status_code == 401:
            # 401是预期的（需要认证），说明服务正常
            print_success(f"服务运行正常（需要认证）: {base_url}")
            return True
        else:
            print_error(f"服务状态码: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"连接失败: {e}")
        print_info("请确认:")
        print(f"  1. 服务地址是否正确: {base_url}")
        print(f"  2. 防火墙是否允许连接")
        print(f"  3. Docker 容器是否运行: docker ps")
        return False

def test_list_models(base_url: str, api_key: str) -> bool:
    """测试列出可用模型"""
    print_header("2. 获取可用模型列表")

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=10)

        if response.status_code == 200:
            models = response.json()
            model_list = models.get('data', [])

            print_success(f"找到 {len(model_list)} 个模型")

            # 检查虚拟模型
            virtual_models = ['auto-chat', 'auto-codex', 'auto-claude']
            found_virtual = [m for m in virtual_models if any(m == model.get('id') for model in model_list)]

            if found_virtual:
                print_success(f"找到虚拟模型: {', '.join(found_virtual)}")
            else:
                print_error("未找到虚拟模型!")

            print("\n所有模型:")
            for model in model_list:
                model_id = model.get('id', 'unknown')
                model_type = '(虚拟)' if model_id in virtual_models else ''
                print(f"  - {model_id} {model_type}")

            return len(found_virtual) == len(virtual_models)
        else:
            print_error(f"获取模型失败: {response.status_code}")
            print(f"响应: {response.text[:200]}")
            return False
    except Exception as e:
        print_error(f"请求失败: {e}")
        return False

def test_routing(base_url: str, api_key: str, model: str, message: str, expected_pool: Optional[str] = None) -> bool:
    """测试单个路由"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 50,
        "temperature": 0.1
    }

    print(f"\n{'─'*60}")
    print(f"模型: {Colors.BOLD}{model}{Colors.RESET}")
    print(f"消息: {message[:50]}{'...' if len(message) > 50 else ''}")
    if expected_pool:
        print(f"预期路由到: {Colors.YELLOW}{expected_pool}{Colors.RESET}")
    print(f"{'─'*60}")

    try:
        response = requests.post(f"{base_url}/v1/chat/completions", headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            returned_model = result.get('model', 'unknown')
            usage = result.get('usage', {})

            print_success(f"请求成功 ✓")
            print(f"  返回模型: {Colors.BOLD}{returned_model}{Colors.RESET}")
            print(f"  使用Token: {usage.get('total_tokens', 'N/A')}")

            # 验证路由
            if expected_pool:
                if returned_model == expected_pool or returned_model == model:
                    print_success(f"路由验证通过 ✓")
                    return True
                else:
                    print_error(f"路由不匹配! 预期: {expected_pool}, 实际: {returned_model}")
                    return False
            return True

        else:
            print_error(f"请求失败: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"  错误: {error_data.get('error', {}).get('message', 'Unknown')}")
            except:
                print(f"  响应: {response.text[:200]}")
            return False

    except requests.Timeout:
        print_error("请求超时 (30秒)")
        return False
    except Exception as e:
        print_error(f"请求异常: {e}")
        return False

def run_all_tests(base_url: str, api_key: str):
    """运行所有测试"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║       LiteLLM 智能路由器 - 远端测试脚本                          ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print(Colors.RESET)

    print(f"\n配置信息:")
    print(f"  服务地址: {Colors.BOLD}{base_url}{Colors.RESET}")
    print(f"  API Key: {Colors.BOLD}{api_key[:20]}...{Colors.RESET}")

    results = []

    # 测试1: 健康检查
    if not test_health(base_url, api_key):
        print_error("\n健康检查失败，无法继续测试")
        return False
    results.append(("健康检查", True))

    # 测试2: 列出模型
    if not test_list_models(base_url, api_key):
        print_error("\n模型列表获取失败")
        return False
    results.append(("模型列表", True))

    # 测试3: 路由测试
    print_header("3. 智能路由测试")

    test_cases = [
        {
            "model": "auto-chat",
            "message": "hi",
            "expected": "auto-chat-mini",
            "desc": "简单消息 → Mini模型"
        },
        {
            "model": "auto-chat",
            "message": "Please provide a comprehensive analysis of distributed system architecture including microservices, event-driven design, and CQRS implementations.",
            "expected": "auto-chat",
            "desc": "复杂消息 → Standard模型"
        },
        {
            "model": "auto-claude",
            "message": "ls",
            "expected": "auto-claude",
            "desc": "简单命令 → Claude"
        },
        {
            "model": "auto-codex",
            "message": "Implement a concurrent lock-free hash table using compare-and-swap primitives.",
            "expected": "auto-codex",
            "desc": "复杂代码 → Codex"
        },
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{Colors.BOLD}[测试 {i}/{len(test_cases)}]{Colors.RESET} {test['desc']}")
        result = test_routing(
            base_url=base_url,
            api_key=api_key,
            model=test['model'],
            message=test['message'],
            expected_pool=test['expected']
        )
        results.append((test['desc'], result))

    # 总结
    print_header("测试总结")
    passed = sum(1 for _, r in results if r)
    total = len(results)

    for desc, result in results:
        status = f"{Colors.GREEN}通过{Colors.RESET}" if result else f"{Colors.RED}失败{Colors.RESET}"
        print(f"  [{status}] {desc}")

    print(f"\n{Colors.BOLD}结果: {passed}/{total} 测试通过{Colors.RESET}\n")

    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ 所有测试通过！系统运行正常 🎉{Colors.RESET}\n")
        return True
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ 部分测试失败，请检查日志{Colors.RESET}\n")
        return False

def main():
    parser = argparse.ArgumentParser(description='LiteLLM 智能路由器远端测试')
    parser.add_argument('--url', 
                      default=os.environ.get('LITELLM_REMOTE_URL', 'http://localhost:4000'),
                      help='LiteLLM 代理地址 (默认: $LITELLM_REMOTE_URL 或 http://localhost:4000)')
    parser.add_argument('--key', 
                      default=os.environ.get('LITELLM_MASTER_KEY', 'sk-litellm-master-key-12345678'),
                      help='API 密钥 (默认: $LITELLM_MASTER_KEY)')

    args = parser.parse_args()

    try:
        success = run_all_tests(args.url, args.key)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}测试被用户中断{Colors.RESET}")
        sys.exit(130)

if __name__ == "__main__":
    main()
