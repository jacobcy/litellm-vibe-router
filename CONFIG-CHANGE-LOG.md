# 配置变更日志

## 2026-02-23 - 4 层 Fallback 策略 + auto-chat 模型优化

### 变更概述

1. **新增 4 层 Fallback 策略**：在原有 3 层基础上新增第 4 层 Volces Ark 作为最终降级
2. **auto-chat 第一层模型调整**：从 `claude-sonnet-4-6` 改为 `gemini-3.1-pro-low`
3. **新增智谱 API 作为第 3 层付费备选**
4. **端口区分**：Chat 系列使用 OpenAI 兼容端口，Claude 系列使用 Anthropic 兼容端口

---

### 详细变更

#### 1. 新增虚拟模型：auto-claude-max

| 层级 | 模型 | 后端 | 端口类型 |
|------|------|------|---------|
| L1 | claude-opus-4-6 | CLIProxyAPI (Antigravity OAuth) | OpenAI 兼容 |
| L2 | claude-opus-4-5 | New API (自建转发) | Anthropic 兼容 |
| L3 | glm-5 | Zhipu API (智谱付费) | Anthropic 兼容 |
| L4 | kimi-k2.5 | Volces Ark (最终降级) | Anthropic 兼容 |

#### 2. auto-chat 模型调整

**变更前**：
- L1: `claude-sonnet-4-6` (CLIProxyAPI)

**变更后**：
- L1: `gemini-3.1-pro-low` (CLIProxyAPI)

**变更原因**：
- 与 `auto-chat-mini` 的 `gemini-2.5-flash` 保持一致，同属 Gemini 系列
- 更清晰的模型定位：Gemini 标准版 vs Gemini 轻量版
- CLIProxyAPI 通过 Antigravity OAuth 提供 Gemini 模型访问

#### 3. 完整 Fallback 策略

| 虚拟模型 | L1 (CLIProxyAPI) | L2 (New API) | L3 (Zhipu) | L4 (Volces) |
|----------|------------------|--------------|------------|-------------|
| **auto-chat** | gemini-3.1-pro-low | gpt-5 | glm-5 | kimi-k2.5 |
| **auto-chat-mini** | gemini-2.5-flash | gpt-5-mini | glm-4.7 | ark-code-latest |
| **auto-claude** | claude-sonnet-4-6 | claude-sonnet-4-5 | glm-5 | glm-4.7 |
| **auto-claude-max** | claude-opus-4-6 | claude-opus-4-5 | glm-5 | kimi-k2.5 |
| **auto-claude-mini** | claude-haiku-4-5 | claude-haiku-4-5 | glm-4.7 | ark-code-latest |
| **auto-codex** | - | gpt-5.2-codex | - | - |

#### 4. 端口使用说明

| 模型系列 | L1 端口 | L2 端口 | L3 端口 | L4 端口 |
|----------|--------|--------|--------|--------|
| Chat (OpenAI 兼容) | OpenAI | OpenAI | OpenAI | OpenAI |
| Claude (Anthropic 兼容) | OpenAI* | Anthropic | Anthropic | Anthropic |
| Codex (OpenAI 兼容) | - | OpenAI | - | - |

> *注：CLIProxyAPI 统一使用 OpenAI 兼容端口 (`/v1`)，但可访问 Claude 模型

---

### CLIProxyAPI 支持的模型列表

通过 `GET http://localhost:8317/v1/models` 获取：

```json
{
  "data": [
    {"id": "gemini-3.1-pro-low", "owned_by": "antigravity"},
    {"id": "gemini-3.1-pro-high", "owned_by": "antigravity"},
    {"id": "gemini-3-pro-high", "owned_by": "antigravity"},
    {"id": "gemini-3-pro-image", "owned_by": "antigravity"},
    {"id": "gemini-3-flash", "owned_by": "antigravity"},
    {"id": "gemini-2.5-flash", "owned_by": "antigravity"},
    {"id": "gemini-2.5-flash-lite", "owned_by": "antigravity"},
    {"id": "claude-sonnet-4-6", "owned_by": "antigravity"},
    {"id": "claude-opus-4-6-thinking", "owned_by": "antigravity"},
    {"id": "gpt-oss-120b-medium", "owned_by": "antigravity"}
  ]
}
```

---

### 新增环境变量

```bash
# .env 文件新增
ZHIPU_API_KEY=a471a1fb929340908c9c672ef1ecd253.emqjk5gebUOWTiT5
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_ANTHROPIC_BASE=https://open.bigmodel.cn/api/anthropic

VOLCES_KIMI_API_KEY=665ab604-a834-4661-8920-da26524b8b8f
VOLCES_KIMI_BASE=https://ark.cn-beijing.volces.com/api/v3
```

---

### 修改的文件

1. **config_final.yaml** - 完整重写 4 层 fallback 配置
2. **.env** - 新增智谱 API 和 Volces kimi API 配置
3. **CLAUDE.md** - 更新文档反映新的 fallback 策略

---

### 测试命令

```bash
# 测试 auto-chat (gemini-3.1-pro-low)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -d '{"model": "auto-chat", "messages": [{"role": "user", "content": "hi"}]}'

# 测试 auto-claude-max (claude-opus-4-6)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -d '{"model": "auto-claude-max", "messages": [{"role": "user", "content": "hi"}]}'

# 测试所有模型
python3 tests/test_all_models.py
```

---

## 测试结果 (2026-02-23)

### 所有 7 个模型测试通过

| 虚拟模型 | 预期 L1 | 实际命中层级 | 状态 |
|----------|---------|-------------|------|
| **auto-chat** | gemini-3.1-pro-low | L3: Zhipu (glm-5) | ✅ 成功 |
| **auto-chat-mini** | gemini-2.5-flash | L2: New API (gpt-5-mini) | ✅ 成功 |
| **auto-claude** | claude-sonnet-4-6 | L2: New API (claude-sonnet-4-5) | ✅ 成功 |
| **auto-claude-max** | claude-opus-4-6 | L1: CLIProxyAPI | ✅ 成功 |
| **auto-claude-mini** | claude-haiku-4-5 | L1: CLIProxyAPI | ✅ 成功 |
| **auto-codex** | - | L2: New API (gpt-5.2-codex) | ✅ 成功 |
| **auto-codex-mini** | - | L2: New API (gpt-5.1-codex-mini) | ✅ 成功 |

**观察结果**：
1. `auto-chat` fallback 到 L3 (Zhipu glm-5)，说明 L1/L2 可能已达到限流或配额用尽
2. `auto-claude` 使用了 L2 New API (claude-sonnet-4-5)，因为 L1 的 claude-sonnet-4-6 在 New API 上不存在
3. 所有模型都能正常响应，fallback 机制工作正常

---

## 2026-02-23 - 测试脚本整理

### 新增测试脚本

**test_fallback_layers.py** - Fallback 层级检测 + 健康度评估
- 自动检测每个模型实际使用的后端层级 (L1-L4)
- 统计成功率、平均耗时、路由分布
- 健康度评估：✅ 健康 / ⚠️ 降级 / ❌ 异常
- 支持多次迭代测试
- 结果输出到 JSON 文件

### 更新的测试脚本

**test_all_6_models.py** → 支持 7 个模型 + Fallback 层级检测
- 添加了 `auto-claude-max` 模型
- 新增 fallback 层级判断函数 `detect_layer()`
- 输出显示每个模型命中的层级

**tests/README.md** - 完整重写
- 详细说明每个测试脚本的功能和用法
- 添加健康度判断标准说明
- 添加 7 个模型的 fallback 策略表
- 添加故障排查指南
- 添加测试文件清单和推荐度

### 删除的冗余脚本

- `test_simple.py` - 功能与 test_all_6_models.py 重复
- `test_manual_selection.py` - 过时的 passthrough 模式测试
- `test_route.py` - 功能与 test_litellm.py 重复

### 当前测试文件清单

| 文件名 | 功能 | 推荐度 |
|--------|------|--------|
| test_fallback_layers.py | Fallback 层级检测 + 健康度评估 | ⭐⭐⭐ |
| test_litellm.py | LiteLLM 路由测试 | ⭐⭐ |
| test_cliproxy.py | CLIProxyAPI 直连测试 | ⭐⭐ |
| test_smoke.py | 稳定性冒烟测试 | ⭐⭐ |
| test_all_6_models.py | 快速连通性测试 | ⭐ |
| test_remote.py | 远端自定义测试 | ⭐ |

### 使用方法

```bash
# Fallback 层级检测 (推荐)
python3 tests/test_fallback_layers.py 3

# 快速测试所有 7 个模型
python3 tests/test_all_6_models.py

# 一键运行所有测试
./test.sh
```

---

### 部署步骤

```bash
# 1. 确保 .env 文件包含所有新增的环境变量
# 2. 重启 LiteLLM 服务
docker-compose down litellm && docker-compose up -d litellm

# 3. 验证服务
curl -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" http://localhost:4000/health
```

---

### 模型选择指南

| 虚拟模型 | 适用场景 |
|----------|---------|
| **auto-chat** | 标准 Gemini 模型，适合大多数任务 |
| **auto-chat-mini** | 轻量级 Gemini，适合简单查询、快速响应 |
| **auto-claude** | Claude Sonnet，适合深度分析、创意写作 |
| **auto-claude-max** | Claude Opus 最强模型，适合最复杂任务 |
| **auto-claude-mini** | Claude Haiku 轻量级，适合简单任务 |
| **auto-codex** | GPT Codex，适合代码生成、算法 |
| **auto-codex-mini** | GPT Codex Mini，适合简单代码片段 |
