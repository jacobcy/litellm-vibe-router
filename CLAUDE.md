# CLAUDE.md

Project documentation for LiteLLM Intelligent Router with 3-tier fallback strategy.

---

## Project Overview

**Architecture**: LiteLLM Proxy + 3-Layer Fallback Strategy  
**Tech Stack**: Python 3.9+, Docker, LiteLLM Proxy, Redis, PostgreSQL  
**Core Feature**: Virtual models with manual selection + automatic fallback on failures

**Current Status**:
- ✅ **6 Virtual Models**: auto-chat, auto-chat-mini, auto-claude, auto-claude-mini, auto-codex, auto-codex-mini
- ✅ **Manual Model Selection**: Users choose standard vs mini variants
- ✅ **3-Layer Fallback**: CLIProxyAPI (OAuth) → New API → Volces Ark
- 🚧 **Auto Complexity Routing**: Disabled (Next Plan - needs more testing and real-world data)

### Virtual Models & Fallback Strategy

```
6 Virtual Models (All Configured):
  ✅ auto-chat          (3 layers): Claude Sonnet 4-6 → gpt-5 → glm-4.7
  ✅ auto-chat-mini     (3 layers): Gemini 2.5 Flash → gpt-5-mini → ark-code
  ✅ auto-claude        (2 layers): Claude Sonnet 4-5 → glm-4.7
  ✅ auto-claude-mini   (2 layers): Claude Haiku 4-5 → glm-4.7
  ✅ auto-codex         (1 layer):  gpt-5.2-codex (New API only)
  ✅ auto-codex-mini    (1 layer):  gpt-5.1-codex-mini (New API only)

Fallback Layers:
  L1: CLIProxyAPI (Antigravity OAuth) - Free tier with quota
  L2: New API (自建转发) - Unlimited usage
  L3: Volces Ark (商业付费) - Paid fallback
```

---

## Quick Commands

```bash
# Deployment
./deploy.sh                           # Auto-deploy all services
docker-compose restart litellm        # Restart after config changes

# Testing
./test.sh                             # Run full test suite (auto-loads tests/.env)
python3 tests/test_all_6_models.py    # Quick test all 6 models
python3 tests/test_remote.py --url http://server:4000 --key sk-xxx

# Manual test
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -d '{"model": "auto-chat", "messages": [{"role": "user", "content": "hi"}]}'

# Health check (requires authentication!)
curl -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  http://localhost:4000/health

# Monitoring
docker logs -f litellm-vibe-router 2>&1 | grep VIBE-ROUTER
docker logs litellm-vibe-router 2>&1 | grep "PASSTHROUGH\|Hook triggered"
```

**Admin UI**: `http://localhost:4000/ui/` (admin / from .env) - Generate Virtual Keys here  
**Test Config**: Copy [tests/.env.example](tests/.env.example) to `tests/.env` and add your key

---

## Request Flow

```
Client → LiteLLM (4000) → Virtual Model Selection (Manual)
  ├─ auto-chat: Standard tasks (claude-sonnet-4-6) with 3-layer fallback
  ├─ auto-chat-mini: Lightweight tasks (gemini-2.5-flash) with 3-layer fallback
  ├─ auto-claude: Claude tasks (claude-sonnet-4-5) with 2-layer fallback
  ├─ auto-claude-mini: Simple Claude (claude-haiku-4-5) with 2-layer fallback
  ├─ auto-codex: Code tasks (gpt-5.2-codex) New API only
  └─ auto-codex-mini: Simple code (gpt-5.1-codex-mini) New API only
    → Router → L1: CLIProxyAPI (OAuth) → L2: New API → L3: Ark API
```

**Model Selection Guide**:
- **auto-chat**: Complex reasoning, long context, multi-step tasks
- **auto-chat-mini**: Simple queries, quick responses, Q&A
- **auto-claude**: Deep analysis, creative writing, complex reasoning
- **auto-claude-mini**: Simple tasks, quick responses, lightweight
- **auto-codex**: Complex code generation, algorithms, refactoring
- **auto-codex-mini**: Simple code snippets, syntax help, quick fixes

### Fallback Strategy (All Models)

## Key Files

**[vibe_router.py](vibe_router.py)** - Router plugin (metadata tracking only)
- Currently in **passthrough mode** - no automatic routing
- Adds metadata: `routing_mode: manual_selection`, `selected_model`
- `async_pre_call_hook()` - **Returns data unmodified** (L118-160)
- 🚧 **Next Plan**: Auto-complexity routing (commented out, L162-210)

**[config_final.yaml](config_final.yaml)** - LiteLLM configuration
- `model_list`: Virtual models + fallback chains with `fallback_order`
- ⚠️ Use `os.environ/VAR` not `${VAR}` for API keys
- ⚠️ Must add callbacks in BOTH `general_settings` AND `litellm_settings`

**[docker-compose.yml](docker-compose.yml)** - Services orchestration
- Environment: `PYTHONPATH=/app` + `env_file: .env`
- Volumes: Plugin mounted at `/app/vibe_router.py:ro`

**[.env](/.env)** - Secrets (gitignored)
- `LITELLM_MASTER_KEY`, `UI_USERNAME`, `UI_PASSWORD`
- `CHAT_AUTO_API_KEY` (CLIProxyAPI), `NEW_API_KEY`, `ARK_API_KEY`

---

## Code Style & Configuration

### Python Essentials
- **Type hints**: `def func(x: str) -> bool:`
- **Error handling**: Log errors, return fallback (never `except: pass`)
- **Async hooks**: Must return modified `data` dict

### Critical Patterns
```python
# LiteLLM Hook (MUST return data)
async def async_pre_call_hook(self, ..., data: Dict, ...) -> Optional[Dict]:
    data["model"] = target_model
    return data  # ← Required, or model becomes None
```

```yaml
# Environment Variables (use os.environ/ syntax)
api_key: os.environ/NEW_API_KEY  # ✅ Correct
api_key: "${NEW_API_KEY}"       # ❌ Won't expand

# Callback Registration (BOTH required)
general_settings:
  callbacks: [vibe_router.router_instance]
litellm_settings:
  callbacks: [vibe_router.router_instance]
```

### Virtual Model Configuration
```yaml
# L1: Use actual backend model
- model_name: auto-chat
  litellm_params:
    model: "claude-sonnet-4-6"  # Antigravity model
    api_key: os.environ/CHAT_AUTO_API_KEY

# L2-L3: Same model_name with fallback_order
- model_name: auto-chat
  litellm_params:
    model: "gpt-5"
  model_info:
    fallback_order: 2
```

---

## Troubleshooting

### Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Hook Not Executing** | Plugin loads but no routing | Add `callbacks: [vibe_router.router_instance]` to `litellm_settings` |
| **Env Vars Not Expanding** | API calls fail with `"${VAR}"` | Use `os.environ/VAR` not `${VAR}` |
| **Model Not Found** | 429/404 from CLIProxyAPI | Use actual backend models (e.g., `gemini-2.5-flash`) |
| **Pydantic Validation** | `model_info.tier` error | Only use `"free"`/`"paid"` or remove tier |
| **Health Check 401** | Unauthorized on `/health` | `/health` endpoint requires `Authorization: Bearer ${KEY}` |
| **Health Check Timeout** | Request times out after 15s | `/health` checks all backends, needs 30-45s timeout |
| **Test Script 401** | Tests fail with wrong key | Ensure `tests/.env` has correct `LITELLM_MASTER_KEY` |
| **Hardcoded Keys** | Scripts use wrong API key | Never hardcode keys, always use `${LITELLM_MASTER_KEY}` |

### Critical Warnings

**⚠️ Health Endpoint Requires Authentication**
```bash
# ❌ Wrong - will return 401
curl http://localhost:4000/health

# ✅ Correct
curl -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" http://localhost:4000/health
```

**⚠️ Health Check is Slow (30-45 seconds)**  
The `/health` endpoint validates all configured backend models by making actual API calls. This is expected behavior and ensures real connectivity status.

**⚠️ Environment Variable Loading in Scripts**
```bash
# ❌ Wrong - variables not exported to Python
source .env
python3 script.py

# ✅ Correct - export variables
set -a  # Auto-export mode
source .env
set +a
python3 script.py
```

**⚠️ Response Content Reading**
```python
# ❌ Wrong - content can only be read once
response = requests.post(...)
print(response.content)  # First read
print(response.content)  # Returns empty!

# ✅ Correct - save or use .json()
response = requests.post(...)
data = response.json()  # Parse once
print(data)
```

**⚠️ Hardcoded API Keys in Scripts**
```bash
# ❌ Never do this
curl -H "Authorization: Bearer sk-litellm-master-key-12345678" ...

# ✅ Always use environment variables
curl -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" ...
```

**⚠️ Working Directory for Scripts**
```bash
# test.sh and deploy.sh must run from project root
cd /path/to/liteLLM  # Ensure correct directory
./deploy.sh          # ✅ Correct
./test.sh            # ✅ Correct
```

---

## Development

**Add Virtual Model**: Edit `SIMPLE_TASK_TARGETS` → Add 3 layers in `config_final.yaml` → Restart  
**Modify Complexity**: Edit `_calculate_complexity()` or `COMPLEXITY_THRESHOLD = 50`  
**Change Backend**: L1(OAuth)=model names, L2(NewAPI)=keep gpt-5, L3(Ark)=openai/glm-4.7

---

## 🚧 Next Plan: Auto Complexity Routing

**Current Status**: Disabled (commented out in [vibe_router.py](vibe_router.py#L162-210))

**Why Disabled**:
- Algorithm needs more testing with real-world data
- Manual selection is more reliable and predictable
- Focus on stable basic service first

**Future Implementation**:
1. Collect real request data and complexity patterns
2. Train/tune prediction model with user feedback
3. Add A/B testing framework to validate routing accuracy
4. Implement gradual rollout with fallback to manual mode

**When to Enable**:
- After gathering ≥1000 production requests
- Complexity prediction accuracy >90%
- User satisfaction metrics validated

---

## Quick Reference

| Item | Value |
|------|-------|
| LiteLLM Port | 4000 |
| CLIProxyAPI Port | 8317 |
| Plugin Hook | `async_pre_call_hook` (must return data) |
| Hook Order | Auth → Alias → **Hook** → Router → Backend |
| Environment Syntax | `os.environ/VAR` (not `${VAR}`) |
| Test Command | `./test.sh` (auto-loads tests/.env) |
| Log Filter | `grep VIBE-ROUTER` or `grep "ROUTING DECISION"` |
| Health Check | Requires auth, takes 30-45s |
| Response.content | Can only be read **once** per request |

**Virtual Models**: `auto-chat`, `auto-chat-mini`, `auto-claude`, `auto-claude-mini`, `auto-codex`, `auto-codex-mini`  
**Backends**: CLIProxyAPI (OAuth) → New API (自建) → Volces Ark (付费)

**Required Environment Variables**:
- Root `.env`: `LITELLM_MASTER_KEY`, `CHAT_AUTO_API_KEY`, `NEW_API_KEY`, `ARK_API_KEY`, `CLIPROXY_MANAGEMENT_KEY`
- Test `tests/.env`: `LITELLM_MASTER_KEY`, `LITELLM_BASE_URL` (must match root `.env` key)
