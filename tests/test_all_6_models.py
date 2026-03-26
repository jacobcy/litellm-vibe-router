#!/usr/bin/env python3
"""快速测试所有 7 个虚拟模型 + Fallback 层级检测"""
import os
import requests

API_KEY = os.environ.get('LITELLM_MASTER_KEY', 'sk-xY93Zr8Bp1TEebwDCkDQqA')
BASE_URL = os.environ.get('LITELLM_BASE_URL', 'http://localhost:4000')

MODELS = [
    "auto-chat",
    "auto-chat-mini",
    "auto-claude",
    "auto-claude-max",
    "auto-claude-mini",
    "auto-codex",
    "auto-codex-mini",
]

# Fallback 层级判断
def detect_layer(model, response_model, content=""):
    """根据返回的模型名称判断命中了哪一层"""
    rm = response_model.lower()
    content_lower = content.lower()

    # L1: CLIProxyAPI
    if "gemini-3.1" in rm or "gemini-2.5-flash" in rm:
        return "L1"
    if "claude-sonnet-4-6" in rm or "claude-opus-4-6" in rm or "claude-haiku-4-5" in rm:
        return "L1"

    # L2: New API
    if "gpt-5" in rm and "codex" not in rm:
        return "L2"
    if "claude-sonnet-4-5" in rm or "claude-opus-4-5" in rm:
        return "L2"
    if "gpt-5.2-codex" in rm or "gpt-5.1-codex" in rm:
        return "L2"

    # L3: Zhipu API
    if "glm-5" in rm or "glm-4.7" in rm:
        return "L3"
    if "glm" in content_lower and "z.ai" in content_lower:
        return "L3"

    # L4: Volces Ark
    if "kimi" in rm or "ark-code" in rm:
        return "L4"

    return "?"

def test_model(model_name):
    """测试单个模型"""
    url = f"{BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            returned_model = data.get('model', 'unknown')
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            layer = detect_layer(model_name, returned_model, content)
            print(f"✅ {model_name:20s} → {returned_model:25s} [L{layer}] OK")
            return True
        else:
            print(f"❌ {model_name:20s} → HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {model_name:20s} → Error: {e}")
        return False

if __name__ == "__main__":
    print("="*70)
    print("测试所有 7 个虚拟模型 + Fallback 层级检测")
    print("="*70)

    results = {}
    for model in MODELS:
        results[model] = test_model(model)

    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"通过：{passed}/{total}")

    if passed == total:
        print("\n🎉 所有模型测试通过！")
    else:
        print("\n⚠️  部分模型测试失败")
        for model, result in results.items():
            if not result:
                print(f"  - {model}")
