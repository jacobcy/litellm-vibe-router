# LiteLLM Intelligent Virtual Router

## 🎯 Overview

This project implements **intelligent model routing** for LiteLLM Proxy, enabling automatic model selection based on request complexity. Users send requests to virtual models (`auto-chat`, `auto-codex`, `auto-claude`), and the system automatically routes to appropriate physical models based on query complexity and rate limits.

### Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────────┐      ┌──────────┐
│   Client    │─────▶│  LiteLLM Proxy   │─────▶│  Vibe Router    │─────▶│ New API  │
│             │      │   Port 4000      │      │    Plugin       │      │ Port 3000│
└─────────────┘      └──────────────────┘      └─────────────────┘      └──────────┘
                              │                         │
                              ▼                         ▼
                        Virtual Models           Intelligent Routing
                        - auto-chat       ┌──▶ Simple → Mini Models
                        - auto-codex      │    Complex → Main Models
                        - auto-claude     ├──▶ Rate Limit Fallback
                                          │    Wildcard Passthrough
                                          └──▶ Direct Model Access
```

## ✨ Key Features

- **Intelligent Routing**: Analyzes message complexity to select optimal model
- **Dual-Level Routing**:
  - **Simple queries** → route to lightweight models (cost-effective)
  - **Complex queries** → route to powerful models with rate limit fallback
- **Wildcard Passthrough**: Any model can be requested directly
- **Zero Client Changes**: Use virtual model names, routing is transparent
- **Cost Optimization**: Simple queries use cheaper models automatically
- **Detailed Logging**: Real-time routing decisions visible in logs
- **Admin UI**: Built-in management interface at port 4000

## 📋 Prerequisites

- Docker & Docker Compose
- Python 3.9+ (for testing)
- `.env` configured in project root

> `new-api` is now managed by this project and started by `docker-compose.yml`.

## 🚀 Quick Start

### 1. Deploy

```bash
chmod +x deploy.sh QUICKSTART.sh
git submodule update --init --recursive
./deploy.sh up
```

This will:
- Start LiteLLM proxy, New API, PostgreSQL, and Redis
- Start CLIProxyAPI for auto-chat isolation (port 8317)
- Verify plugin loading
- Check service health

### 1.1 One-Click Script Usage

```bash
# Full stack start (default)
./deploy.sh
./deploy.sh up

# Update all services (pull latest images + recreate)
./deploy.sh update

# Start only selected services
./deploy.sh up --services litellm,new-api
./deploy.sh update --services litellm

# Show help
./deploy.sh --help
```

### 2. Test Routing

```bash
# Run comprehensive test suite
python3 test_simple.py
```

### 3. Manual Test

```bash
# Simple query (routes to gpt-5-mini)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto-chat",
    "messages": [{"role": "user", "content": "hi"}]
  }'

# Complex query (routes to openai/gpt-5)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto-claude",
    "messages": [{
      "role": "user",
      "content": "Implement a distributed algorithm for concurrent data processing"
    }]
  }'

# Direct model access (wildcard passthrough)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5",
    "messages": [{"role": "user", "content": "test"}]
  }'
```

## 📁 File Structure

```
liteLLM/
├── vibe_router.py          # Main plugin implementation
├── config_final.yaml       # LiteLLM configuration
├── docker-compose.yml      # Docker deployment (LiteLLM, New API, PostgreSQL, Redis, CLIProxyAPI)
├── new-api/data/           # New API persistent data directory
├── CLIProxyAPI/            # Submodule: CLIProxyAPI service
├── cliproxyapi.config.yaml # CLIProxyAPI runtime config
├── deploy.sh               # Automated deployment script
├── test_simple.py          # Simple routing tests
├── test_route.py           # Comprehensive test suite
├── test_remote.py          # Remote testing script
├── verify.py              # Verification script
├── QUICKSTART.sh          # Quick start script
└── README.md              # This file
```

## 🔧 Configuration

### Virtual Models

Three virtual entry points with intelligent routing:

| Virtual Model | Simple Route       | Complex Route         | Rate Limit Fallback |
|--------------|--------------------|-----------------------|-------------------|
| `auto-chat`  | gpt-5-mini        | openai/gpt-5         | gpt-5            |
| `auto-codex` | gpt-5.1-codex-mini| openai/gpt-5.2-codex | gpt-5.2-codex    |
| `auto-claude`| claude-haiku-4-5  | anthropic/claude-sonnet-4-5 | claude-sonnet-4-5 |

**auto-chat Isolation**

`auto-chat` uses a dedicated API base (CLIProxyAPI on port 8317) with its own key to
reduce 429 errors and keep traffic isolated.

### Routing Logic

The plugin calculates a **complexity score** based on:

1. **Message Length**: Longer messages → higher score
2. **Simple Keywords**: `ls`, `cat`, `hi`, `test` → lower score
3. **Complex Keywords**: `implement`, `analyze`, `algorithm`, `design` → higher score
4. **Code Blocks**: Presence of ` ``` ` → higher score
5. **Sentence Count**: Multiple sentences → higher score
6. **Conversation History**: Long threads → higher score

**Decision Threshold**: Score < 50 = Simple, Score ≥ 50 = Complex

### Wildcard Passthrough

Any model can be requested directly:

| Pattern      | Provider  | API Base                     | Notes |
|--------------|-----------|-----------------------------|-------|
| `claude-*`   | anthropic| `http://host.docker.internal:3000` | No /v1 |
| `anthropic/*`| anthropic| `http://host.docker.internal:3000` | No /v1 |
| `*`          | openai    | `http://host.docker.internal:3000/v1` | Default |

### Customizing Routes

Edit `vibe_router.py`:

```python
# Simple task targets
SIMPLE_TASK_TARGETS = {
    "auto-chat": "gpt-5-mini",
    "auto-codex": "gpt-5.1-codex-mini",
    "auto-claude": "claude-haiku-4-5"
}

# Complexity threshold (default: 50)
COMPLEXITY_THRESHOLD = 50  # Adjust to tune routing sensitivity
```

### Authentication

**For API Requests:**
```
Authorization: Bearer sk-litellm-master-key-12345678
```

**For Admin UI:**
- URL: `http://localhost:4000/ui/`
- Username: `admin`
- Password: `admin123`

### Environment Variables

Backend API key is configured in `config_final.yaml`:
```yaml
NEW_API_KEY: sk-6cjjC0tbmfadXNqsrIABJO6nPBuYXKHtacIU0YFvoRxfTAQh
```

auto-chat dedicated API:
```yaml
CHAT_AUTO_API_BASE: http://cliproxyapi:8317/v1
CHAT_AUTO_API_KEY: sk-auto-chat-proxy-12345678
```

New API local endpoint used by LiteLLM:
```yaml
NEW_API_BASE: http://host.docker.internal:3000/v1
NEW_API_ANTHROPIC_BASE: http://host.docker.internal:3000
```

## 📊 Monitoring

### View Real-Time Logs

```bash
# All logs
docker logs -f litellm-vibe-router

# Plugin logs only
docker logs -f litellm-vibe-router 2>&1 | grep VIBE-ROUTER

# Routing decisions
docker logs -f litellm-vibe-router 2>&1 | grep "SIMPLE\|COMPLEX"
```

### Check Service Health

```bash
# Health endpoint
curl http://localhost:4000/health

# List models
curl -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  http://localhost:4000/v1/models
```

### Access Admin UI

```bash
# Open in browser
open http://localhost:4000/ui/

# Login with:
# Username: admin
# Password: admin123
```

## 🔬 Advanced: How It Works

### LiteLLM Request Lifecycle

```
1. Client Request
   ↓
2. Master Key Validation
   ↓
3. async_pre_call_hook ← VIBE ROUTER EXECUTES HERE
   │ - Analyze message complexity
   │ - Simple query: Rewrite model to lightweight (e.g., gpt-5-mini)
   │ - Complex query: Keep model as-is for fallback chain
   │ - Add metadata for observability
   ↓
4. Router Model Resolution (pattern matching, groups)
   ↓
5. Rate Limit Fallback (if needed)
   │ - Try primary model
   │ - If rate limited, try fallback model
   ↓
6. LiteLLM API Call → New API → Actual LLM
```

### Routing Decision Flow

```
Request → auto-chat
    ↓
async_pre_call_hook analyzes complexity
    ↓
    ├─ Score < 50 (Simple) → Rewrite to gpt-5-mini
    │                           ↓
    │                         Send to backend directly
    │
    └─ Score >= 50 (Complex) → Keep openai/gpt-5
                               ↓
                             Try openai/gpt-5
                                 ↓ (rate limited)
                             Try gpt-5 (fallback)
```

### Plugin Architecture

```python
class VibeIntelligentRouter(CustomLogger):
    SIMPLE_TASK_TARGETS = {
        "auto-chat": "gpt-5-mini",
        "auto-codex": "gpt-5.1-codex-mini",
        "auto-claude": "claude-haiku-4-5"
    }

    async def async_pre_call_hook(self, ...):
        """
        Fires BEFORE router resolution
        Rewrites model for simple queries to lightweight models
        """

        # 1. Calculate complexity
        score = self._calculate_complexity(messages)

        # 2. Select target for simple queries
        if score < 50:
            target_model = self.SIMPLE_TASK_TARGETS[original_model]
            data["model"] = target_model
            # Simple queries skip fallback chain

        # 3. CRITICAL: Return modified data
        return data
```

## 🐛 Troubleshooting

### Plugin Not Loading

**Symptoms**: No `[VIBE-ROUTER]` logs, 400 errors

**Fix**:
```bash
# Check plugin logs
docker logs litellm-vibe-router 2>&1 | grep VIBE-ROUTER

# Verify PYTHONPATH
docker exec litellm-vibe-router env | grep PYTHONPATH

# Test plugin import
docker exec litellm-vibe-router python3 -c "import vibe_router; print('OK')"
```

### Admin UI Not Connecting to DB

**Symptoms**: "Authentication Error, Not connected to DB!"

**Fix**:
```bash
# Check PostgreSQL status
docker ps | grep postgres

# Verify DATABASE_URL
docker exec litellm-vibe-router env | grep DATABASE_URL

# Restart services
docker-compose down
docker-compose up -d
```

### Model Not Found Errors

**Symptoms**: `ProxyModelNotFoundError: model=auto-chat`

**Cause**: Virtual models not defined in `config_final.yaml`

**Fix**: Ensure virtual models exist in `model_list` with fallback chain:
```yaml
model_list:
  # Virtual entry point
  - model_name: auto-chat
    litellm_params:
      model: "openai/gpt-5"

  # Rate limit fallback
  - model_name: auto-chat
    litellm_params:
      model: "gpt-5"
    model_info:
      fallback_order: 2
      fallback_reason: "rate_limit"
```

### Connection Errors

**Symptoms**: `Connection refused` to New API

**Fix**:
```bash
# Check New API is running
curl http://localhost:3000/v1/models

# Verify docker host gateway
docker exec litellm-vibe-router ping -c 1 host.docker.internal
```

## 📝 License

MIT

## 🎓 References

- [LiteLLM Docs](https://docs.litellm.ai/)
- [Custom Callbacks](https://docs.litellm.ai/docs/proxy/custom_callbacks)
- [Admin UI](https://docs.litellm.ai/docs/proxy/admin_ui)
