# 降级链路配置总结

## 🎯 快速参考

### 模型降级策略（修正版）

```
┌──────────────────────────────────────────────────────────────┐
│                     降级链路总览                              │
└──────────────────────────────────────────────────────────────┘

1️⃣ auto-chat (3层降级) - CLIProxyAPI 专用
   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
   │ CLIProxyAPI │ ───▶ │  New API    │ ───▶ │ Volces Ark  │
   │   :8317     │ 429  │   :3000     │ 429  │   glm-4.7   │
   └─────────────┘      └─────────────┘      └─────────────┘
   openai/gpt-5         gpt-5                 glm-4.7
   (简单任务用 gpt-5-mini)                    (简单任务用 ark-code-latest)

2️⃣ auto-claude (2层降级)
   ┌─────────────┐      ┌─────────────┐
   │  New API    │ ───▶ │ Volces Ark  │
   │   :3000     │ 429  │   glm-4.7   │
   └─────────────┘      └─────────────┘
   claude-sonnet-4-5    glm-4.7

3️⃣ auto-codex (1层，无降级) - Volces 不支持 Codex
   ┌─────────────┐
   │  New API    │ ───▶ ✗ 失败直接报错
   │   :3000     │
   └─────────────┘
   gpt-5.2-codex

```

---

## 📋 配置验证清单

### ✅ 已完成

- [x] 3层降级：auto-chat → CLIProxyAPI → New API → Ark
- [x] 2层降级：auto-claude → New API → Ark
- [x] 1层配置：auto-codex → New API (无降级)
- [x] .env 文件创建 (Ark API 密钥已配置)
- [x] .gitignore 保护 .env 文件
- [x] config_final.yaml 更新完成

### ⚠️ 待配置

- [ ] `.env` 中的 `CHAT_AUTO_API_KEY`
- [ ] `.env` 中的 `NEW_API_KEY`
- [ ] `cliproxyapi.config.yaml` 中的 `api-keys[0]`
- [ ] `cliproxyapi.config.yaml` 中的 `codex-api-key[0].api-key`

---

## 🔑 密钥配置对照表

| 服务 | 配置文件 | 字段 | 用途 |
|------|---------|------|------|
| **Volces Ark** | `.env` | `ARK_API_KEY` | ✅ 已配置: 665ab604-... |
| **CLIProxyAPI** | `.env` | `CHAT_AUTO_API_KEY` | ⚠️ 需配置 |
| **New API** | `.env` | `NEW_API_KEY` | ⚠️ 需配置 |
| **CLIProxyAPI 认证** | `cliproxyapi.config.yaml` | `api-keys[0]` | ⚠️ 需配置 |
| **CLIProxyAPI 上游** | `cliproxyapi.config.yaml` | `codex-api-key[0].api-key` | ⚠️ 需配置 |

---

## 🚀 快速部署命令

```bash
# 1. 配置密钥
vim .env                        # 填入 CHAT_AUTO_API_KEY 和 NEW_API_KEY
vim cliproxyapi.config.yaml     # 填入第16行和第27行的真实密钥

# 2. 部署服务
./deploy.sh

# 3. 测试 auto-chat (3层)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{"model": "auto-chat", "messages": [{"role": "user", "content": "hi"}]}'

# 4. 测试 auto-claude (2层)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{"model": "auto-claude", "messages": [{"role": "user", "content": "hello"}]}'

# 5. 测试 auto-codex (1层，无降级)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{"model": "auto-codex", "messages": [{"role": "user", "content": "quicksort"}]}'

# 6. 查看日志
docker logs -f litellm-vibe-router 2>&1 | grep -E "VIBE-ROUTER|Fallback"
```

---

## 💡 关键差异点

### CLIProxyAPI 服务范围

| 模型 | 使用 CLIProxyAPI | 原因 |
|------|----------------|------|
| auto-chat ✅ | ✅ 第1层优先 | CLIProxyAPI 提供 OpenAI 兼容接口 |
| auto-chat-mini ✅ | ✅ 第1层优先 | 同上 |
| auto-claude ❌ | ❌ 不使用 | 直接走 New API |
| auto-codex ❌ | ❌ 不使用 | 直接走 New API |

### Volces Ark 降级范围

| 模型 | 可降级到 Ark | 原因 |
|------|-------------|------|
| auto-chat ✅ | ✅ 第3层 | Ark 支持 OpenAI 接口 (glm-4.7) |
| auto-chat-mini ✅ | ✅ 第3层 | Ark 支持 OpenAI 接口 (ark-code-latest) |
| auto-claude ✅ | ✅ 第2层 | Ark 支持 Claude 接口 (glm-4.7) |
| auto-codex ❌ | ❌ 无降级 | ⚠️ **Ark 不支持 Codex 接口** |

---

## 📖 完整文档

详细配置说明请查看: `CLIPROXYAPI-SETUP.md`
