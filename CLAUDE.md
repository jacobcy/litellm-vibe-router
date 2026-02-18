# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

This is a LiteLLM Proxy with an intelligent routing plugin (`vibe_router.py`) that automatically selects the optimal AI model based on query complexity. Users send requests to virtual models (`chat-auto`, `codex-auto`, `claude-auto`), and the system routes to appropriate physical models with automatic rate limit fallback.

---

## Common Commands

### Deployment
```bash
# Deploy all services (LiteLLM, PostgreSQL, Redis)
./deploy.sh

# Or use docker-compose directly
docker-compose up -d

# Stop all services
docker-compose down

# Restart LiteLLM only (after config changes)
docker-compose restart litellm
```

### Testing
```bash
# Run simple routing tests
python3 test_simple.py

# Run comprehensive test suite
python3 test_route.py

# Test specific scenario manually
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-master-key-12345678" \
  -H "Content-Type: application/json" \
  -d '{"model": "chat-auto", "messages": [{"role": "user", "content": "hi"}]}'
```

### Monitoring
```bash
# View all logs
docker logs -f litellm-vibe-router

# View plugin routing decisions only
docker logs litellm-vibe-router 2>&1 | grep VIBE-ROUTER

# Check simple/complex routing
docker logs litellm-vibe-router 2>&1 | grep "SIMPLE\|COMPLEX"

# Check service health
curl http://localhost:4000/health
```

### Admin UI
- URL: `http://localhost:4000/ui/`
- Username: `admin`
- Password: `admin123`

---

## Architecture

### Request Flow

```
Client Request → LiteLLM Proxy (port 4000)
    ↓
Master Key Validation (sk-litellm-master-key-12345678)
    ↓
async_pre_call_hook (vibe_router.py)
    ├─ Analyze message complexity (score 0-∞)
    ├─ If score < 50: Rewrite model to lightweight (e.g., gpt-5-mini)
    └─ If score >= 50: Keep model as-is for fallback chain
    ↓
Router Model Resolution (pattern matching)
    ↓
Rate Limit Fallback (if needed)
    ├─ Try primary model (e.g., openai/gpt-5)
    └─ If rate limited: Try fallback model (e.g., gpt-5)
    ↓
LiteLLM API Call → New API (localhost:3000) → Actual LLM
```

### Virtual Models and Routing

| Virtual Model | Simple Route (<50) | Complex Route (>=50) | Fallback |
|--------------|-------------------|---------------------|----------|
| `chat-auto`  | gpt-5-mini        | openai/gpt-5         | gpt-5    |
| `codex-auto` | gpt-5.1-codex-mini| openai/gpt-5.2-codex | gpt-5.2-codex |
| `claude-auto`| claude-haiku-4-5  | anthropic/claude-sonnet-4-5 | claude-sonnet-4-5 |

### Wildcard Passthrough

Any model can be requested directly:

| Pattern      | Provider  | API Base                           |
|--------------|-----------|-----------------------------------|
| `claude-*`   | anthropic| `http://host.docker.internal:3000` |
| `anthropic/*`| anthropic| `http://host.docker.internal:3000` |
| `*`          | openai    | `http://host.docker.internal:3000/v1` |

Note: Anthropic models use `/v1` endpoint, OpenAI uses `/v1` path.

### Key Files

- `vibe_router.py` - Plugin implementing `VibeIntelligentRouter(CustomLogger)`
  - `SIMPLE_TASK_TARGETS`: Maps virtual models to lightweight models
  - `_calculate_complexity()`: Scores messages based on length, keywords, code blocks
  - `async_pre_call_hook()`: Rewrites model for simple queries, must return modified `data`

- `config_final.yaml` - LiteLLM configuration
  - `model_list`: Defines virtual models + fallback chains (2 layers)
  - `environment_variables`: API keys and backend URLs
  - `litellm_settings.callbacks`: Must include `vibe_router.router_instance`

- `docker-compose.yml` - Service orchestration
  - `postgres`: Database for Admin UI
  - `redis`: Caching for LiteLLM
  - `litellm`: Main proxy with plugin mounted at `/app/vibe_router.py`

---

## Configuration Details

### Backend API Keys

All backend calls use the same key (configured in `config_final.yaml`):
```
sk-6cjjC0tbmfadXNqsrIABJO6nPBuYXKHtacIU0YFvoRxfTAQh
```

### Client Authentication

- **API requests**: Use `sk-litellm-master-key-12345678` as Bearer token
- **Admin UI**: Login with `admin` / `admin123`

### Complexity Scoring

The plugin calculates complexity based on:

1. **Message length**: Longer = higher score (max +200)
2. **Simple keywords**: `ls`, `cat`, `hi`, `test` → -100 each
3. **Complex keywords**: `implement`, `algorithm`, `design` → +150 each
4. **Code blocks**: ` ``` ` or `def ` → +100
5. **Sentence count**: >2 sentences → +50
6. **Conversation history**: >5 messages → +30

Threshold: Score < 50 = Simple, Score ≥ 50 = Complex

To adjust: Edit `COMPLEXITY_THRESHOLD` in `vibe_router.py:175`

---

## Development Notes

### Adding a New Virtual Model

1. Add to `SIMPLE_TASK_TARGETS` in `vibe_router.py`
2. Add virtual entry point + fallback chain to `model_list` in `config_final.yaml`
3. Add simple/complex keywords to `simple_indicators` / `complex_indicators` if needed
4. Restart LiteLLM: `docker-compose restart litellm`

### Fallback Chain Configuration

Each virtual model requires 2 fallback layers in `config_final.yaml`:
```yaml
- model_name: chat-auto          # Layer 1: Primary
  litellm_params:
    model: "openai/gpt-5"

- model_name: chat-auto          # Layer 2: Rate limit fallback
  litellm_params:
    model: "gpt-5"
  model_info:
    fallback_order: 2
    fallback_reason: "rate_limit"
```

Note: The 3rd layer (final fallback) was removed because simple queries are already routed directly by the plugin, bypassing the fallback chain.

### Plugin Hook Critical Path

The `async_pre_call_hook` MUST return the modified `data` object:

```python
data["model"] = target_model  # Rewrite the model
return data  # ← CRITICAL: Without this, changes are lost
```

### Environment Variables for Containers

The plugin is mounted into the container at `/app/vibe_router.py`. PYTHONPATH is set to `/app` so LiteLLM can import it:

```yaml
environment:
  - PYTHONPATH=/app
```

To test plugin import inside container:
```bash
docker exec litellm-vibe-router python3 -c "import vibe_router; print('OK')"
```
