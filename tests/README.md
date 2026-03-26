# LiteLLM 测试脚本快速指南

## 环境设置

```bash
# 1. 创建虚拟环境（只需一次）
python3 -m venv .venv

# 2. 安装依赖
source .venv/bin/activate
pip install requests
```

## 获取测试 Token

1. 访问 LiteLLM 管理界面：http://localhost:4000/ui/
2. 登录（用户名：admin, 密码：admin123）
3. 在左侧菜单找到 "Keys" → "Create Key"
4. 复制生成的 key（格式：`sk-xxxxxx`）

## 配置测试环境

```bash
# 复制配置模板
cp tests/.env.example tests/.env

# 编辑 tests/.env，填入真实的 key
# LITELLM_MASTER_KEY=sk-你生成的 key
```

---

## 测试脚本说明

### 1. test_fallback_layers.py - Fallback 层级检测 ⭐ 推荐

**功能**: 测试每个虚拟模型的 actual fallback 层级，评估系统健康度

**测试原理**:
- 发送请求到虚拟模型
- 从返回的 model 字段和响应内容判断实际使用的后端
- 统计每个模型的 fallback 层级分布
- 评估系统健康状态

```bash
# 标准测试（1 次迭代）
source tests/.env
python3 tests/test_fallback_layers.py

# 多次迭代（更准确的统计）
python3 tests/test_fallback_layers.py 3

# 输出测试结果到 JSON
# 结果保存到 tests/fallback_test_results.json
```

**输出示例**:
```
======================================================================
Fallback 层级检测测试
======================================================================
测试配置:
  目标地址：http://localhost:4000
  API Key: sk-xY93Zr8Bp1TEebwDCkDQqA
  迭代次数：3
  测试模型：7 个

[迭代 1/3]
----------------------------------------------------------------------
✅ auto-chat          → glm-5                   [L3  ]    2.34s
✅ auto-chat-mini     → gpt-5-mini              [L2  ]    1.89s
✅ auto-claude        → claude-sonnet-4-5       [L2  ]    3.21s
✅ auto-claude-max    → claude-opus-4-6         [L1  ]    4.56s
✅ auto-claude-mini   → claude-haiku-4-5        [L1  ]    2.10s
✅ auto-codex         → gpt-5.2-codex           [L2  ]    3.45s
✅ auto-codex-mini    → gpt-5.1-codex-mini      [L2  ]    2.87s

======================================================================
测试总结与健康度评估
======================================================================
模型                 成功率        主要层级           平均耗时       健康度
------------------------------------------------------------------------------------
auto-chat             100%        L3                  2.34s       ⚠️  降级
auto-chat-mini        100%        L2                  1.89s       ✅ 健康
auto-claude           100%        L2                  3.21s       ✅ 健康
auto-claude-max       100%        L1                  4.56s       ✅ 健康
auto-claude-mini      100%        L1                  2.10s       ✅ 健康
auto-codex            100%        L2                  3.45s       ✅ 健康
auto-codex-mini       100%        L2                  2.87s       ✅ 健康

整体健康度：健康

⚠️  发现的问题:
  - auto-chat 频繁降级到 L3/L4
```

**健康度判断标准**:
| 状态 | 条件 | 说明 |
|------|------|------|
| ✅ 健康 | 成功率≥80% 且 主要层级=L1/L2 | 模型工作在预期层级 |
| ⚠️ 降级 | 成功率≥80% 但 主要层级=L3/L4 | 上游限流或配额用尽 |
| ❌ 异常 | 成功率<80% | 后端服务异常 |

---

### 2. test_litellm.py - LiteLLM 路由测试

**功能**: 测试 LiteLLM 4000 端口的路由决策和 fallback 行为

```bash
# 加载环境并运行
source tests/.env
python3 tests/test_litellm.py

# 安静模式（仅显示结果摘要）
python3 tests/test_litellm.py --quiet
```

**测试内容**:
- ✅ auto-chat → L1/L2/L3/L4 fallback 验证
- ✅ auto-chat-mini → L1/L2/L3/L4 fallback 验证
- ✅ auto-claude → L1/L2/L3/L4 fallback 验证
- ✅ auto-claude-max → L1/L2/L3/L4 fallback 验证
- ✅ auto-claude-mini → L1/L2/L3/L4 fallback 验证
- ✅ auto-codex → L2 fallback 验证
- ✅ auto-codex-mini → L2 fallback 验证

**输出示例**:
```
===========================================================================
LiteLLM 路由测试 (端口 4000)
===========================================================================
✅ auto-chat          → glm-5                 [L3: Zhipu API]    OK
✅ auto-chat-mini     → gpt-5-mini            [L2: New API]      OK
✅ auto-claude        → claude-sonnet-4-5     [L2: New API]      OK
✅ auto-claude-max    → claude-opus-4-6       [L1: CLIProxyAPI]  OK
✅ auto-claude-mini   → claude-haiku-4-5      [L1: CLIProxyAPI]  OK
✅ auto-codex         → gpt-5.2-codex         [L2: New API]      OK
✅ auto-codex-mini    → gpt-5.1-codex-mini    [L2: New API]      OK
```

---

### 3. test_cliproxy.py - CLIProxyAPI 直连测试

**功能**: 测试 CLIProxyAPI 8317 端口是否正常工作（绕过 LiteLLM）

```bash
# 加载环境并运行
source tests/.env
python3 tests/test_cliproxy.py

# 安静模式
python3 tests/test_cliproxy.py --quiet
```

**测试内容**:
- ✅ auto-chat → CLIProxyAPI 8317
- ✅ auto-chat-mini → CLIProxyAPI 8317
- ✅ auto-claude → CLIProxyAPI 8317
- ✅ auto-claude-max → CLIProxyAPI 8317
- ✅ auto-claude-mini → CLIProxyAPI 8317

**输出示例**:
```
======================================================================
CLIProxyAPI 直连测试 (端口 8317)
======================================================================
✅ auto-chat          → claude-sonnet-4-6   [L1: CLIProxyAPI (:8317)] (245ms)
✅ auto-chat-mini     → gemini-2.5-flash    [L1: CLIProxyAPI (:8317)] (189ms)
✅ auto-claude        → claude-sonnet-4-6   [L1: CLIProxyAPI (:8317)] (312ms)
✅ auto-claude-max    → claude-opus-4-6     [L1: CLIProxyAPI (:8317)] (456ms)
✅ auto-claude-mini   → claude-haiku-4-5    [L1: CLIProxyAPI (:8317)] (178ms)
```

---

### 4. test_smoke.py - 冒烟测试

**功能**: 对每个模型连续测试多次，分析稳定性和路由分布

```bash
# 标准测试（7 次迭代，间隔 3 秒）
source tests/.env
python3 tests/test_smoke.py

# 自定义迭代次数（如 10 次）
python3 tests/test_smoke.py 10

# 安静模式
python3 tests/test_smoke.py --quiet
```

**测试内容**:
- 所有 7 个虚拟模型 × N 次迭代
- 每次间隔 3 秒
- 统计成功率、响应时间、路由分布、fallback 次数

**输出示例**:
```
======================================================================
冒烟测试 - auto-chat (7 次迭代)
======================================================================
[1/7] ✅      234ms → glm-5               [L3: Zhipu API]
[2/7] ✅      198ms → gpt-5               [L2: New API]      ⚠️ FALLBACK
[3/7] ✅      189ms → gemini-3.1-pro-low  [L1: CLIProxyAPI]
[4/7] ✅      256ms → glm-5               [L3: Zhipu API]
[5/7] ❌        -- → Timeout              [FAILED]
[6/7] ✅      201ms → glm-5               [L3: Zhipu API]
[7/7] ✅      223ms → glm-5               [L3: Zhipu API]

----------------------------------------------------------------------
统计总结 - auto-chat
----------------------------------------------------------------------
  ✅ 成功率：6/7 (85.7%)
  ⏱️  响应时间：189-256ms (avg: 217ms, median: 212ms)
  🗺️  路由分布:
      L1: CLIProxyAPI: 1 次 (16.7%)
      L2: New API: 1 次 (16.7%)
      L3: Zhipu API: 4 次 (66.7%)
  ⚠️  Fallback 触发：5 次
```

---

### 5. test_all_6_models.py - 快速测试

**功能**: 快速测试所有 7 个虚拟模型（单次）

```bash
source tests/.env
python3 tests/test_all_6_models.py
```

**输出示例**:
```
============================================================
测试所有 7 个虚拟模型
============================================================
✅ auto-chat          → glm-5                OK
✅ auto-chat-mini     → gpt-5-mini           OK
✅ auto-claude        → claude-sonnet-4-5    OK
✅ auto-claude-max    → claude-opus-4-6      OK
✅ auto-claude-mini   → claude-haiku-4-5     OK
✅ auto-codex         → gpt-5.2-codex        OK
✅ auto-codex-mini    → gpt-5.1-codex-mini   OK

测试总结
通过：7/7
🎉 所有模型测试通过！
```

---

### 6. test_remote.py - 远端测试

**功能**: 支持自定义 URL 和 API Key 的远端测试

```bash
# 使用默认配置
python3 tests/test_remote.py

# 自定义 URL 和 Key
python3 tests/test_remote.py --url http://server:4000 --key sk-xxx

# 使用环境变量
export LITELLM_REMOTE_URL=http://server:4000
export LITELLM_MASTER_KEY=sk-xxx
python3 tests/test_remote.py
```

---

## 一键测试脚本

```bash
# 创建快捷脚本
cat > test.sh << 'EOF'
#!/bin/bash
set -a
source tests/.env
set +a

echo "Running all tests..."
echo ""

echo "=== Fallback 层级检测 ==="
python3 tests/test_fallback_layers.py 3
echo ""

echo "=== CLIProxyAPI 直连测试 ==="
python3 tests/test_cliproxy.py
echo ""

echo "=== LiteLLM 路由测试 ==="
python3 tests/test_litellm.py
echo ""

echo "=== 冒烟测试 ==="
python3 tests/test_smoke.py 7
EOF

chmod +x test.sh
./test.sh
```

---

## 环境变量说明

| 变量名 | 用途 | 默认值 |
|--------|------|--------|
| `LITELLM_BASE_URL` | LiteLLM 地址 | http://localhost:4000 |
| `LITELLM_MASTER_KEY` | LiteLLM 主密钥 | sk-litellm-master-key |
| `CLIPROXY_BASE_URL` | CLIProxyAPI 地址 | http://localhost:8317 |
| `CHAT_AUTO_API_KEY` | CLIProxyAPI 密钥 | sk-auto-chat-proxy-key |
| `NEW_API_KEY` | New API 密钥 | your-new-api-key |
| `ARK_API_KEY` | Volces Ark 密钥 | 已配置 |
| `ZHIPU_API_KEY` | 智谱 API 密钥 | 已配置 |

---

## 路由层级说明

```
请求 → LiteLLM (4000) → 路由决策 → 后端 API

L1: CLIProxyAPI (:8317)  - OAuth 免费层
       ↓ 失败/限流
L2: New API (:3000)      - 自建转发层
       ↓ 失败/限流
L3: Zhipu API            - 智谱付费层
       ↓ 失败/限流
L4: Volces Ark           - 最终降级层
```

**7 个虚拟模型的 fallback 策略**:

| 虚拟模型 | L1 | L2 | L3 | L4 |
|----------|------|------|------|------|
| auto-chat | gemini-3.1-pro-low | gpt-5 | glm-5 | kimi-k2.5 |
| auto-chat-mini | gemini-2.5-flash | gpt-5-mini | glm-4.7 | ark-code-latest |
| auto-claude | claude-sonnet-4-6 | claude-sonnet-4-5 | glm-5 | glm-4.7 |
| auto-claude-max | claude-opus-4-6 | claude-opus-4-5 | glm-5 | kimi-k2.5 |
| auto-claude-mini | claude-haiku-4-5 | claude-haiku-4-5 | glm-4.7 | ark-code-latest |
| auto-codex | - | gpt-5.2-codex | - | - |
| auto-codex-mini | - | gpt-5.1-codex-mini | - | - |

---

## 故障排查

### CLIProxyAPI 连接失败

```bash
# 检查 CLIProxyAPI 是否运行
docker ps | grep cli-proxy-api

# 检查日志
docker logs cli-proxy-api

# 测试连通性
curl http://localhost:8317/v1/models -H "Authorization: Bearer sk-chat-auto-proxy-12345678"
```

### LiteLLM 返回 401

```bash
# 确认 LITELLM_MASTER_KEY 正确
echo $LITELLM_MASTER_KEY

# 检查容器内环境变量
docker exec litellm-vibe-router env | grep LITELLM
```

### 冒烟测试成功率低

1. 检查后端 API 是否限流
2. 查看 LiteLLM 日志：`docker logs litellm-vibe-router | grep -i fallback`
3. 增加迭代间隔：修改测试脚本中的 `INTERVAL_SECONDS` 参数

### Fallback 层级异常

运行 `test_fallback_layers.py` 查看详细层级分布：

```bash
python3 tests/test_fallback_layers.py 3
```

如果 auto-chat 频繁降级到 L3/L4，说明 L1/L2 可能已达到限流或配额用尽。

---

## 常见问题

**Q: 为什么 auto-chat 返回了 glm-5 而不是 gemini-3.1-pro-low？**
A: 这说明触发了 fallback 降级。CLIProxyAPI (L1) 或 New API (L2) 可能限流或不可用，自动降级到了 Zhipu API (L3)。

**Q: 如何只测试某一个模型？**
A: 编辑测试脚本，修改 `MODELS` 列表只保留你要测试的模型。

**Q: 冒烟测试的迭代次数可以修改吗？**
A: 可以，命令行参数指定：`python3 tests/test_smoke.py 10`（10 次迭代）

**Q: 如何判断系统是否健康？**
A: 运行 `test_fallback_layers.py`，查看健康度评估：
- ✅ 健康：成功率≥80% 且 主要层级=L1/L2
- ⚠️ 降级：成功率≥80% 但 主要层级=L3/L4
- ❌ 异常：成功率<80%

---

## 测试文件清单

| 文件名 | 功能 | 推荐度 |
|--------|------|--------|
| test_fallback_layers.py | Fallback 层级检测 + 健康度评估 | ⭐⭐⭐ |
| test_litellm.py | LiteLLM 路由测试 | ⭐⭐ |
| test_cliproxy.py | CLIProxyAPI 直连测试 | ⭐⭐ |
| test_smoke.py | 稳定性冒烟测试 | ⭐⭐ |
| test_all_6_models.py | 快速连通性测试 | ⭐ |
| test_remote.py | 远端自定义测试 | ⭐ |
