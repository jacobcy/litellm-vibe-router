# CLAUDE.md

Project documentation for LiteLLM Intelligent Router with 3-tier fallback strategy.

---

## Project Overview

**Architecture**: LiteLLM Proxy + Intelligent Router Plugin + 3-Layer Fallback  
**Tech Stack**: Python 3.9+, Docker, LiteLLM Proxy, Redis, PostgreSQL  
**Core Feature**: Virtual models auto-route based on complexity (< 50 = simple, ≥ 50 = complex)

### 3-Layer Fallback Strategy

```
chat-auto (3 layers):
  L1: CLIProxyAPI (Antigravity OAuth) → claude-sonnet-4-6 / gemini-2.5-flash
  L2: New API (自建转发) → gpt-5 / gpt-5-mini (模型转换)
  L3: Volces Ark (商业付费) → glm-4.7 / ark-code-latest

codex-auto (1 layer): New API only
claude-auto (2 layers): New API → Volces Ark
```

---

## Quick Commands

```bash
# Deployment
./deploy.sh                           # Auto-deploy all services
docker-compose restart litellm        # Restart after config changes

# Testing (reads from .env)
python3 tests/test_simple.py          # Quick routing test
python3 tests/test_route.py           # Comprehensive tests
python3 tests/test_remote.py          # Remote server tests
python3 tests/test_remote.py --url http://server:4000 --key sk-xxx  # Custom args

# Manual test
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -d '{"model": "chat-auto", "messages": [{"role": "user", "content": "hi"}]}'

# Monitoring
docker logs -f litellm-vibe-router 2>&1 | grep VIBE-ROUTER
docker logs litellm-vibe-router 2>&1 | grep "SIMPLE\|COMPLEX"
```

**Admin UI**: `http://localhost:4000/ui/` (admin / from .env)  
**Test Config**: Copy [tests/.env.example](tests/.env.example) to `.env` for test credentials

---

## Request Flow

```
Client → LiteLLM (4000) → async_pre_call_hook (complexity check)
  ├─ Simple (<50): Rewrite to lightweight model (gemini-2.5-flash)
  └─ Complex (≥50): Keep original for fallback chain
    → Router → L1: CLIProxyAPI (OAuth) → L2: New API → L3: Ark API
```

### Complexity Scoring

- Message length (max +200), Simple words (-100), Complex words (+150)
- Code blocks (+100), Sentences >2 (+50), History >5 (+30)
- **Threshold**: `COMPLEXITY_THRESHOLD = 50` in [vibe_router.py](vibe_router.py#L175)

---

## Key Files

**[vibe_router.py](vibe_router.py)** - Intelligent router plugin
- `SIMPLE_TASK_TARGETS = {"chat-auto": "chat-auto-mini", ...}` (L49-51)
- `async_pre_call_hook()` - **MUST return modified `data`** (L127-218)

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
- model_name: chat-auto
  litellm_params:
    model: "claude-sonnet-4-6"  # Antigravity model
    api_key: os.environ/CHAT_AUTO_API_KEY

# L2-L3: Same model_name with fallback_order
- model_name: chat-auto
  litellm_params:
    model: "gpt-5"
  model_info:
    fallback_order: 2
```

---

## Troubleshooting

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Hook Not Executing** | Plugin loads but no routing | Add `callbacks: [vibe_router.router_instance]` to `litellm_settings` |
| **Env Vars Not Expanding** | API calls fail with `"${VAR}"` | Use `os.environ/VAR` not `${VAR}` |
| **Model Not Found** | 429/404 from CLIProxyAPI | Use actual backend models (e.g., `gemini-2.5-flash`) |
| **Pydantic Validation** | `model_info.tier` error | Only use `"free"`/`"paid"` or remove tier |

---

## Development

**Add Virtual Model**: Edit `SIMPLE_TASK_TARGETS` → Add 3 layers in `config_final.yaml` → Restart  
**Modify Complexity**: Edit `_calculate_complexity()` or `COMPLEXITY_THRESHOLD = 50`  
**Change Backend**: L1(OAuth)=model names, L2(NewAPI)=keep gpt-5, L3(Ark)=openai/glm-4.7

---

## Quick Reference

| Item | Value |
|------|-------|
| LiteLLM Port | 4000 |
| CLIProxyAPI Port | 8317 |
| Plugin Hook | `async_pre_call_hook` (must return data) |
| Hook Order | Auth → Alias → **Hook** → Router → Backend |
| Environment Syntax | `os.environ/VAR` (not `${VAR}`) |
| Test Command | `python3 test_route.py` |
| Log Filter | `grep VIBE-ROUTER` or `grep "ROUTING DECISION"` |

**Virtual Models**: `chat-auto`, `chat-auto-mini`, `codex-auto`, `claude-auto`  
**Backends**: CLIProxyAPI (OAuth) → New API (自建) → Volces Ark (付费)
