# CLIProxyAPI 集成配置说明

## 🎯 架构概览

### 差异化降级链路设计

**不同模型有不同的降级策略**：

```
┌─────────┐
│ Client  │ 发送请求
└────┬────┘
     │
     ▼
┌──────────────────────────────────────────┐
│  LiteLLM Proxy (localhost:4000)          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  1️⃣ vibe_router.py 智能路由:            │
│     • 简单任务 → auto-chat-mini          │
│     • 复杂任务 → 保持原模型               │
│                                           │
│  2️⃣ LiteLLM Router 差异化降级:          │
└──────┬────────────────────────────────────┘
       │
       ├──────────────────────┬──────────────────────┬─────────────────────┐
       ▼                      ▼                      ▼                     ▼
┌────────────────┐    ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│  auto-chat     │    │  auto-claude   │    │  auto-codex    │    │                │
│  (3层降级)     │    │  (2层降级)     │    │  (1层，无降级) │    │                │
└────────────────┘    └────────────────┘    └────────────────┘    └────────────────┘
       │                      │                      │
       ▼                      ▼                      ▼
🥇 CLIProxyAPI         🥇 New API             🥇 New API
   :8317                  :3000                  :3000
   OpenAI 兼容            Claude API             Codex API
       │                      │                      ✓ 完成
       ↓ 429/失败             ↓ 429/失败
🥈 New API             🥈 Volces Ark
   :3000                  glm-4.7
       │                      ✓ 完成
       ↓ 429/失败
🥉 Volces Ark
   glm-4.7 / ark-code-latest
       ✓ 完成
```

### 为什么降级层数不同？

| 模型 | 降级层数 | 原因 |
|------|---------|------|
| **auto-chat** | 3层 | CLIProxyAPI 提供 OpenAI 兼容接口，专门服务 auto-chat |
| **auto-claude** | 2层 | Volces Ark 支持 Claude 接口，可作为最终降级 |
| **auto-codex** | 1层（无降级） | ⚠️ Volces Ark **不支持** Codex 接口，无法降级 |

### 模型映射关系（修正版）

| 虚拟模型 | 简单任务目标 | 第1层(优先) | 第2层(降级) | 第3层(最终) |
|---------|------------|------------|------------|------------|
| **auto-chat** (复杂) | - | openai/gpt-5 @ CLIProxyAPI | gpt-5 @ New API | glm-4.7 @ Ark |
| **auto-chat** (简单) | auto-chat-mini | gpt-5-mini @ CLIProxyAPI | gpt-5-mini @ New API | ark-code-latest @ Ark |
| **auto-claude** | - | claude-sonnet-4-5 @ New API | glm-4.7 @ Ark | - |
| **auto-codex** | - | gpt-5.2-codex @ New API | - | - |

---

## 📋 配置检查清单

### ✅ 已完成的配置

1. **CLIProxyAPI 源码**: 已下载到 `CLIProxyAPI/` 目录
2. **Docker Compose**: cliproxyapi 服务已配置
   - 端口: 8317
   - 配置文件: `cliproxyapi.config.yaml` (已挂载)
   - 认证目录: `cliproxy_auth` volume
3. **LiteLLM 配置**: `config_final.yaml` 3层降级链已配置
   - auto-chat → CLIProxyAPI (第1级) → New API (第2级) → Volces Ark (第3级)
4. **路由插件**: `vibe_router.py` 已更新
   - 简单任务使用 `auto-chat-mini`
5. **环境变量**: `.env` 文件已创建
   - Volces Ark API 密钥已配置
6. **Git 忽略**: `.gitignore` 已更新，.env 不会被提交

### ⚠️ 待完成的配置

#### 1. CLIProxyAPI 上游 API 密钥 (必须!)

编辑 `cliproxyapi.config.yaml`，替换以下占位符:

```yaml
# ⚠️ 第16行: LiteLLM 访问 CLIProxyAPI 的认证密钥
api-keys:
  - "sk-auto-chat-proxy-12345678"  # 替换成真实密钥

# ⚠️ 第27行: CLIProxyAPI 转发到上游 AI 服务的密钥
codex-api-key:
  - api-key: "你的真实Codex-API-Key"  # 替换成真实密钥
```

**如何获取 Codex API Key:**
- OpenAI 官方: https://platform.openai.com/api-keys
- 或使用第三方代理商（PackyCode、AICodeMirror 等）

#### 2. 同步更新 .env 文件

编辑 `.env` 文件，配置所有层级的 API 密钥:

```bash
# Level 3: Volces Ark API (已配置 ✅)
ARK_API_KEY=665ab604-a834-4661-8920-da26524b8b8f
ARK_OPENAI_BASE=https://ark.cn-beijing.volces.com/api/coding
ARK_CLAUDE_BASE=https://ark.cn-beijing.volces.com/api/coding

# Level 1: CLIProxyAPI (⚠️ 需要替换)
CHAT_AUTO_API_KEY=你的真实密钥

# Level 2: New API (⚠️ 需要替换)
NEW_API_KEY=你的真实密钥
```

---

## 🚀 部署步骤

### 1. 初始化 CLIProxyAPI 子模块 (已完成 ✅)

```bash
cd /Users/chenyi/liteLLM
git submodule update --init --recursive
# 或直接克隆
git clone https://github.com/router-for-me/CLIProxyAPI.git CLIProxyAPI
```

### 2. 配置 API 密钥 (必须!)

#### 方式1: 使用 .env 文件 (推荐)

```bash
# 拷贝模板文件
cp .env.example .env

# 编辑 .env 文件
vim .env

# 需要配置的变量:
# - ARK_API_KEY (第3层 - 已填写)
# - CHAT_AUTO_API_KEY (第1层 - 需要替换)
# - NEW_API_KEY (第2层 - 需要替换)
```

#### 方式2: 直接编辑配置文件

```bash
# 编辑 CLIProxyAPI 配置
vim cliproxyapi.config.yaml
# 替换第16行和第27行的占位符

# 编辑 LiteLLM 配置 (可选，优先使用 .env)
vim config_final.yaml
# 替换环境变量部分
```

### 3. 启动所有服务

```bash
./deploy.sh
```

服务启动后:
- **CLIProxyAPI**: http://localhost:8317
- **LiteLLM Proxy**: http://localhost:4000
- **Admin UI**: http://localhost:4000/ui/ (admin / admin123)

### 4. 验证环境变量加载

```bash
# 检查容器内是否正确加载 .env 变量
docker exec litellm-vibe-router env | grep -E "ARK_|CHAT_AUTO_|NEW_API_"
```

### 5. 测试差异化降级链路

#### 测试 auto-chat 第1级 (CLIProxyAPI)

```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto-chat",
    "messages": [{"role": "user", "content": "hi"}]
  }'
```

**预期**:
- vibe_router 检测为简单任务 → 改写为 `auto-chat-mini`
- 请求发送到 CLIProxyAPI (8317)
- 日志显示: `ROUTING DECISION: auto-chat-mini → cliproxyapi:8317`

#### 测试 auto-chat 第2级降级 (New API)

```bash
# 停止 CLIProxyAPI
docker stop cli-proxy-api

# 发送简单请求
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{"model": "auto-chat", "messages": [{"role": "user", "content": "hello"}]}'
```

**预期**:
- LiteLLM 尝试第1级 (CLIProxyAPI) 失败
- 自动降级到第2级 (New API localhost:3000)
- 日志显示: `Fallback triggered → gpt-5-mini @ host.docker.internal:3000`

#### 测试 auto-chat 第3级最终降级 (Volces Ark)

```bash
# 保持 CLIProxyAPI 停止，假设 New API 也不可用

# 发送请求
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{"model": "auto-chat", "messages": [{"role": "user", "content": "test"}]}'
```

**预期**:
- LiteLLM 尝试第1级失败 → 第2级失败
- 最终降级到第3级 (Volces Ark API)
- 日志显示: `Fallback triggered → ark-code-latest @ ark.cn-beijing.volces.com`
- 使用 ARK_API_KEY 成功返回响应

---

#### 测试 auto-claude (2层降级)

```bash
# 第1级: New API
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto-claude",
    "messages": [{"role": "user", "content": "explain async/await"}]
  }'
```

**预期**:
- 请求发送到 New API (3000)
- 使用 claude-sonnet-4-5 模型

```bash
# 模拟 New API 失败，测试降级到 Volces Ark
# (假设 New API 不可用)

curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{"model": "auto-claude", "messages": [{"role": "user", "content": "test"}]}'
```

**预期**:
- 第1级 (New API) 失败
- 降级到第2级 (Volces Ark)
- 使用 glm-4.7 模型

---

#### 测试 auto-codex (无降级)

```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto-codex",
    "messages": [{"role": "user", "content": "write a quicksort function"}]
  }'
```

**预期**:
- 请求发送到 New API (3000)
- 使用 gpt-5.2-codex 模型
- ⚠️ 如果失败，**不会降级**（因为 Volces 不支持 Codex）
- 直接返回错误

---

## 📊 监控和日志

### 查看路由决策

```bash
# 查看所有 vibe_router 日志
docker logs litellm-vibe-router 2>&1 | grep VIBE-ROUTER

# 查看简单/复杂任务分类
docker logs litellm-vibe-router 2>&1 | grep "SIMPLE\|COMPLEX"

# 查看降级触发
docker logs litellm-vibe-router 2>&1 | grep -i fallback
```

### 查看 CLIProxyAPI 日志

```bash
# 实时日志
docker logs -f cli-proxy-api

# 过滤请求日志
docker logs cli-proxy-api 2>&1 | grep -E "POST|GET|model"
```

---

## 🔧 常见问题

### Q1: CLIProxyAPI 启动失败，提示 "no such file or directory"

**原因**: CLIProxyAPI 目录不存在或子模块未初始化

**解决**:
```bash
cd /Users/chenyi/liteLLM
git submodule update --init --recursive
# 或直接克隆
git clone https://github.com/router-for-me/CLIProxyAPI.git CLIProxyAPI
```

### Q2: 请求一直返回 401 Unauthorized

**原因**: API 密钥配置不一致

**检查优先级**:
1. `.env` 文件中的 `CHAT_AUTO_API_KEY`
2. `cliproxyapi.config.yaml` 的 `api-keys` (第16行)
3. Docker Compose 从 .env 加载变量传递到容器

**调试**:
```bash
# 检查容器内环境变量
docker exec litellm-vibe-router env | grep CHAT_AUTO_API_KEY

# 检查 CLIProxyAPI 配置
cat cliproxyapi.config.yaml | grep -A2 api-keys
```

### Q3: CLIProxyAPI 返回错误 "invalid API key"

**原因**: CLIProxyAPI 转发到上游时，上游 API 密钥无效

**检查**: 
- `cliproxyapi.config.yaml` 第27行的 `codex-api-key`
- 确认该密钥在上游服务有效

### Q4: 第3层降级不工作，Volces Ark API 报错

**检查 .env 文件**:
```bash
# 确认 ARK_API_KEY 已配置
cat .env | grep ARK_API_KEY

# 检查容器内变量加载
docker exec litellm-vibe-router env | grep ARK
```

**确认变量正确传递**:
- docker-compose.yml 的 `env_file: [.env]` 存在
- environment 部分有 `ARK_API_KEY=${ARK_API_KEY}`

### Q5: 降级总是跳过第1层，直接到第2层

**原因**: CLIProxyAPI 可能未启动或不可达

**检查**:
```bash
# 检查 CLIProxyAPI 容器状态
docker ps | grep cli-proxy-api

# 检查 CLIProxyAPI 日志
docker logs cli-proxy-api

# 手动测试 CLIProxyAPI 连通性
curl http://localhost:8317/health || echo "不可达"
```

### Q6: .env 文件被提交到 Git

**解决**:
```bash
# 确认 .gitignore 包含 .env
cat .gitignore | grep ".env"

# 如果已提交，移除并重新提交
git rm --cached .env
git commit -m "Remove .env from git history"

# 永久删除历史记录 (慎用)
git filter-branch --index-filter 'git rm --cached --ignore-unmatch .env' HEAD
```

### Q7: 变量展开失败，配置文件显示 "${ARK_API_KEY}" 原值

**原因**: 
- LiteLLM 不支持在 `litellm_params` 中展开 `${VAR}` 语法
- 必须通过 Docker 环境变量传递

**正确配置**:
```yaml
# config_final.yaml - 使用 ${VAR} 语法
environment_variables:
  ARK_API_KEY: "${ARK_API_KEY}"  # Docker 会展开

# docker-compose.yml - 加载 .env
env_file:
  - .env
environment:
  - ARK_API_KEY=${ARK_API_KEY}  # 传递到容器
```

---

## 📚 参考资料

- **CLIProxyAPI 文档**: `CLIProxyAPI/README_CN.md`
- **LiteLLM 文档**: `CLAUDE.md`, `AGENTS.md`
- **配置示例**: `CLIProxyAPI/config.example.yaml`
- **部署脚本**: `deploy.sh`
- **测试脚本**: `test_simple.py`, `test_route.py`

---

## 🎯 下一步

1. ✅ CLIProxyAPI 源码已下载
2. ✅ .env 文件已创建 (Volces Ark API 已配置)
3. ✅ .gitignore 已更新 (.env 不会被提交)
4. ✅ 3层降级链已配置完成
5. ⚠️ **配置 API 密钥** - 编辑 `.env` 文件:
   - `CHAT_AUTO_API_KEY` (第1层 CLIProxyAPI)
   - `NEW_API_KEY` (第2层 New API)
6. ⚠️ **配置 CLIProxyAPI 上游密钥** - 编辑 `cliproxyapi.config.yaml`:
   - `api-keys` (LiteLLM 访问密钥，第16行)
   - `codex-api-key` (转发到上游的密钥，第27行)
7. ⚠️ **运行 `./deploy.sh` 启动服务**
8. ⚠️ **测试3层降级链路是否工作**

---

**重要提示**: 
- `.env` 文件包含真实 API 密钥，已添加到 .gitignore
- 所有占位符密钥 (`sk-auto-chat-proxy-12345678` 等) 必须替换成真实密钥
- Volces Ark API 密钥已配置在 `.env` 中 (第3层最终降级)
- 部署前请确认所有密钥配置正确，否则服务无法正常工作!

---

## 📚 配置文件总结

### 密钥配置位置

| 文件 | 变量/字段 | 用途 | 当前值 |
|------|----------|------|-------|
| `.env` | `ARK_API_KEY` | 第3层 Volces Ark | ✅ 已配置 |
| `.env` | `CHAT_AUTO_API_KEY` | 第1层 CLIProxyAPI | ⚠️ 占位符 |
| `.env` | `NEW_API_KEY` | 第2层 New API | ⚠️ 占位符 |
| `cliproxyapi.config.yaml` | `api-keys[0]` | LiteLLM → CLIProxyAPI | ⚠️ 占位符 |
| `cliproxyapi.config.yaml` | `codex-api-key[0].api-key` | CLIProxyAPI → 上游 | ⚠️ 占位符 |

### 降级链路配置（修正版）

| 虚拟模型 | 层数 | 第1层 (优先) | 第2层 (降级) | 第3层 (最终) |
|---------|-----|-------------|-------------|-------------|
| **auto-chat** (复杂) | 3层 | openai/gpt-5<br/>@ CLIProxyAPI:8317 | gpt-5<br/>@ New API:3000 | glm-4.7<br/>@ Volces Ark |
| **auto-chat-mini** (简单) | 3层 | gpt-5-mini<br/>@ CLIProxyAPI:8317 | gpt-5-mini<br/>@ New API:3000 | ark-code-latest<br/>@ Volces Ark |
| **auto-claude** | 2层 | claude-sonnet-4-5<br/>@ New API:3000 | glm-4.7<br/>@ Volces Ark | - |
| **auto-codex** | 1层 | gpt-5.2-codex<br/>@ New API:3000 | - | - |

### 重要说明

- ✅ **auto-chat**: CLIProxyAPI 提供专门的 OpenAI 兼容接口，3层降级
- ✅ **auto-claude**: New API → Volces Ark，2层降级  
- ⚠️ **auto-codex**: 仅 New API，**无降级**（Volces 不支持 Codex 接口）

### CLIProxyAPI 使用范围

**仅服务于 auto-chat 和 auto-chat-mini**：
- ✅ auto-chat → CLIProxyAPI
- ✅ auto-chat-mini → CLIProxyAPI
- ❌ auto-codex → 不经过 CLIProxyAPI
- ❌ auto-claude → 不经过 CLIProxyAPI
