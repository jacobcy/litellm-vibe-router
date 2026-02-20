#!/usr/bin/env python3
"""Test manual model selection in passthrough mode."""

import os
import sys
import requests

# Load LITELLM_MASTER_KEY from .env
env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
with open(env_file) as f:
    for line in f:
        if line.startswith('LITELLM_MASTER_KEY='):
            LITELLM_KEY = line.split('=', 1)[1].strip()
            break

BASE_URL = "http://localhost:4000/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {LITELLM_KEY}",
    "Content-Type": "application/json"
}

print("=" * 55)
print("Testing Manual Model Selection (Passthrough Mode)")
print("=" * 55)

# Test 1: auto-chat (standard)
print("\n1️⃣  Testing auto-chat (standard model)...")
resp = requests.post(BASE_URL, headers=HEADERS, json={
    "model": "auto-chat",
    "messages": [{"role": "user", "content": "Say hi"}]
})
data = resp.json()
print(f"Response: {data['choices'][0]['message']['content'][:60]}...")
print(f"Model: {data.get('model', 'N/A')}")

# Test 2: auto-chat-mini (lightweight)
print("\n2️⃣  Testing auto-chat-mini (lightweight model)...")
resp = requests.post(BASE_URL, headers=HEADERS, json={
    "model": "auto-chat-mini",
    "messages": [{"role": "user", "content": "Say hi"}]
})
data = resp.json()
print(f"Response: {data['choices'][0]['message']['content'][:60]}...")
print(f"Model: {data.get('model', 'N/A')}")

print("\n✅ Both models working correctly!")
print("=" * 55)
