#!/usr/bin/env python3
"""快速测试所有6个虚拟模型"""
import os
import requests

API_KEY = os.environ.get('LITELLM_MASTER_KEY', 'sk-xY93Zr8Bp1TEebwDCkDQqA')
BASE_URL = os.environ.get('LITELLM_BASE_URL', 'http://localhost:4000')

MODELS = [
    "auto-chat",
    "auto-chat-mini",
    "auto-claude",
    "auto-claude-mini",
    "auto-codex",
    "auto-codex-mini",
]

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
            print(f"✅ {model_name:20s} → {returned_model:20s} OK")
            return True
        else:
            print(f"❌ {model_name:20s} → HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {model_name:20s} → Error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("测试所有6个虚拟模型")
    print("="*60)
    
    results = {}
    for model in MODELS:
        results[model] = test_model(model)
    
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有模型测试通过！")
    else:
        print("\n⚠️  部分模型测试失败")
        for model, result in results.items():
            if not result:
                print(f"  - {model}")
