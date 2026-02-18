# LiteLLM Intelligent Router - Agent Guidelines

## Project Overview

Intelligent model routing for LiteLLM Proxy. Virtual models auto-route to physical pools based on message complexity.

**Tech Stack**: Python 3.9+, Docker, LiteLLM Proxy, Redis

---

## Build & Test Commands

```bash
# Deployment
./deploy.sh                    # Automated deployment
docker-compose down && up -d   # Manual deployment

# Testing
python3 verify.py              # Quick verification (no API calls)
python3 test_route.py          # Comprehensive test suite
python3 -c "from test_route import test_health; test_health()"  # Single test

# Docker logs
docker logs -f litellm-vibe-router 2>&1 | grep "ROUTING DECISION"
docker logs litellm-vibe-router 2>&1 | grep VIBE-ROUTER
```

---

## Code Style Guidelines

### File Structure
- Shebang: `#!/usr/bin/env python3`
- Module docstring (triple quotes)
- Imports: stdlib → typing → third-party (wrap optional deps in try/except)
- Main guard: `if __name__ == "__main__":`

### Naming Conventions
- Classes: PascalCase (`VibeIntelligentRouter`)
- Functions/Methods: snake_case (`_calculate_complexity`, `async_pre_call_hook`)
- Constants: UPPER_SNAKE_CASE (`COMPLEXITY_THRESHOLD`, `PROXY_URL`)
- Private members: Prefix with underscore (`_log`, `_calculate_complexity`)

### Type Hints (Required)
```python
from typing import Optional, Dict, Any, List, Literal

def test_route(model_name: str, message: str, expected_route: Optional[str] = None) -> bool:
    ...
```

### Imports
```python
# 1. Standard library
import sys
import time
from typing import Optional, Dict, Any

# 2. Third-party (wrap in try/except)
try:
    from litellm.integrations.custom_logger import CustomLogger
    import litellm
except ImportError as e:
    _log(f"✗ Import failed: {e}", "ERROR")
    raise
```

---

## Formatting & Style

- 4 spaces per level (no tabs), max line 100-120 chars
- Docstrings: Describe purpose, args, returns
- Comments: Explain **WHY**, not **WHAT**
- Mark CRITICAL sections: `# CRITICAL: Must return modified data`
- Error handling: Log errors, return fallback (NEVER `except: pass`)

### Error Handling
```python
try:
    result = api_call()
except Exception as e:
    _log(f"ERROR: {e}", "ERROR")
    import traceback
    _log(traceback.format_exc(), "ERROR")
    return default_value
```

---

## Async/Await Patterns

LiteLLM hooks are async - always use `async def`:

```python
class VibeIntelligentRouter(CustomLogger):
    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: Dict,
        call_type: Literal["completion", ...]
    ) -> Optional[Dict]:
        # Critical: MUST return modified data
        data["model"] = new_model
        return data
```

---

## Logging

Always log to stderr for Docker visibility:
```python
import sys
import time

def _log(message: str, level: str = "INFO"):
    """Thread-safe logging to stderr"""
    timestamp = time.strftime("%H:%M:%S")
    sys.stderr.write(f"[{timestamp}] [PREFIX] [{level}] {message}\n")
    sys.stderr.flush()
```

**Prefix**: `[VIBE-ROUTER]`, `[TEST]`, `[DEPLOY]`

---

## Docker & Environment

### PYTHONPATH is Critical
Plugin files must be in `/app` and PYTHONPATH must include it:
```yaml
# docker-compose.yml
environment:
  - PYTHONPATH=/app
volumes:
  - ./vibe_router.py:/app/vibe_router.py:ro
```

### Config References
Use environment variables in YAML:
```yaml
environment_variables:
  NEW_API_BASE: "http://host.docker.internal:3000/v1"

model_list:
  - model_name: chat-auto
    litellm_params:
      api_base: ${NEW_API_BASE}
```

---

## Testing Guidelines

### Test Structure
```python
def test_scenario():
    """Test description"""
    try:
        # Arrange
        setup_data()
        # Act
        result = perform_action()
        # Assert
        if condition:
            print_success("Test passed")
            return True
        else:
            print_error("Test failed")
            return False
    except Exception as e:
        print_error(f"Test exception: {e}")
        return False
```

### Test Data
Use representative messages:
- Simple: "hi", "ls", "cat test.py"
- Complex: "Implement distributed consensus algorithm"

---

## LiteLLM-Specific Rules

### Virtual Models MUST Exist
Always define virtual models in `model_list`:
```yaml
model_list:
  - model_name: chat-auto  # Required for validation
    litellm_params:
      model: "openai/gpt-5"  # Fallback
```

### Hook Execution Order
```
Request → Auth → Model Alias Map → async_pre_call_hook (REWRITE) → Router → API
```

Your hook fires AFTER alias mapping but BEFORE router resolution - perfect timing.

### Critical Return Value
```python
async def async_pre_call_hook(self, ..., data: Dict, ...):
    data["model"] = target_model
    return data  # ← REQUIRED: Without this, model becomes None
```

---

## File Checklist

- [ ] Shebang present (`#!/usr/bin/env python3`)
- [ ] Module docstring
- [ ] Type hints on public functions
- [ ] Error handling with logging
- [ ] Private members prefixed with `_`
- [ ] Constants UPPER_SNAKE_CASE
- [ ] Critical sections marked `# CRITICAL:`
- [ ] No silent exception handling

---

## Quick Reference

**Key Files:**
- `vibe_router.py` - Main plugin (CustomLogger subclass)
- `config_final.yaml` - LiteLLM configuration
- `docker-compose.yml` - Docker deployment
- `test_route.py` - Test suite

**Virtual Models:**
- `chat-auto` → pool-chat-mini / pool-chat-standard
- `codex-auto` → pool-codex-mini / pool-codex-heavy
- `claude-auto` → pool-claude-haiku / pool-claude-sonnet

**Complexity Threshold:** 50 points (lower = simpler route)

---

## Known Issues & Troubleshooting

### 🔴 Issue #1: Hook Not Executing (async_pre_call_hook Silent)

**Symptom**: Plugin loads successfully but `async_pre_call_hook` never fires. Models are not rewritten.

**Root Cause**: LiteLLM's `general_settings.callbacks` only registers success/failure callbacks. To register `async_pre_call_hook`, must also add `callbacks` in `litellm_settings` section.

**Solution**:
```yaml
# config_final.yaml
general_settings:
  callbacks:
    - vibe_router.router_instance  # ✅ Registers success/failure callbacks

litellm_settings:
  callbacks: ["vibe_router.router_instance"]  # ✅ REQUIRED for async_pre_call_hook
```

**Verification**:
```bash
# Check if hook is registered
docker logs litellm-vibe-router 2>&1 | grep "async_pre_call_hook"

# Test routing
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-vibe-master-123" \
  -H "Content-Type: application/json" \
  -d '{"model": "chat-auto", "messages": [{"role": "user", "content": "hi"}]}'
```

---

### 🔴 Issue #2: ModelInfo Validation Error (Invalid Tier)

**Symptom**: Deployment fails with error like:
```
pydantic.ValidationError: 1 validation error for ModelInfo
tier
  Input should be 'free' or 'paid' [type=literal_error]
```

**Root Cause**: LiteLLM's Pydantic model validation restricts `model_info.tier` to only `'free'` or `'paid'`. Custom tier values cause validation failures.

**Solution**:
```yaml
# ❌ WRONG - Will fail deployment
model_info:
  id: "chat-auto"
  tier: "standard"  # Causes ValidationError

# ✅ CORRECT - Remove custom tier or use id only
model_info:
  id: "chat-auto"
  # tier: "standard"  # Remove or comment out

# ✅ OR - Use only allowed values
model_info:
  id: "chat-auto"
  tier: "paid"  # Only 'free' or 'paid' allowed
```

**Note**: If custom tiers are needed for downstream logic, store them elsewhere (e.g., in plugin route_map).

---

### 🔴 Issue #3: Environment Variables Not Expanding

**Symptom**: Config references `${NEW_API_BASE}` but LiteLLM treats it as literal string instead of expanding to actual value.

**Root Cause**: LiteLLM does NOT expand `${VAR}` syntax in `litellm_params` within model configurations.

**Solution**:
```yaml
# ❌ WRONG - ${NEW_API_BASE} won't expand
model_list:
  - model_name: chat-auto
    litellm_params:
      api_base: ${NEW_API_BASE}  # Treated as literal "${NEW_API_BASE}"
      api_key: ${NEW_API_KEY}

# ✅ CORRECT - Hardcode values directly
model_list:
  - model_name: chat-auto
    litellm_params:
      api_base: http://host.docker.internal:3000/v1  # Hardcoded
      api_key: sk-6cjjC0tbmfadXNqsrIABJO6nPBuYXKHtacIU0YFvoRxfTAQh  # Hardcoded
```

**Alternative**: Use environment variables in `docker-compose.yml` and reference them in config if LiteLLM supports it in specific sections (tested - not supported in litellm_params).

---

### 🟡 Issue #4: Container Health Check Unhealthy

**Symptom**: `docker ps` shows `health: unhealthy` but service works correctly.

**Root Cause**: Health check endpoint timing or configuration mismatch.

**Solution**:
```bash
# Check health endpoint directly
curl http://localhost:4000/health

# If working, ignore unhealthy status or adjust health check
# Edit docker-compose.yml:
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s  # Give more time for startup
```

---

### 🟡 Issue #5: New API Response Format Errors

**Symptom**: HTTP 500 error with message:
```
"ResponseReasoningItem is not a valid Pydantic field"
```

**Root Cause**: New API backend returns unknown fields in some model responses (e.g., codex models with `ResponseReasoningItem`).

**Solution**:
1. **LiteLLM side**: Set `drop_params: true` in config (already enabled)
   ```yaml
   litellm_settings:
     drop_params: true  # Drops unknown fields
   ```

2. **New API side**: Fix response format to match OpenAI API spec

3. **Workaround**: Use different models that return valid responses

**Verification**:
```bash
# Test different models
python3 test_route.py  # See which models fail
docker logs litellm-vibe-router 2>&1 | grep "ResponseReasoningItem"
```

---

### 🟡 Issue #6: Timeout on Complex Queries

**Symptom**: Complex message requests timeout after 600s (or configured timeout).

**Root Cause**: Model processing time exceeds `request_timeout` setting.

**Solution**:
```yaml
# config_final.yaml - Increase timeout
litellm_settings:
  request_timeout: 900  # Increase from 600 to 900 seconds

# Or optimize complexity threshold to route to faster models
```

---

## Quick Checklist for Common Issues

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Hook silent | Missing callbacks in litellm_settings | Add `callbacks: ["vibe_router.router_instance"]` |
| Deployment fails | Invalid tier values | Use only `'free'`/`'paid'` or remove tier |
| API base not working | ${VAR} not expanding | Hardcode values directly |
| Unknown field errors | New API response format | Set `drop_params: true` |
| Request timeouts | request_timeout too low | Increase timeout value |
| Model not found | Virtual model missing | Define in model_list |

---
