#!/bin/sh
# Create symlinks for backward compatibility
ln -sf /app/config/litellm_config.yaml /app/litellm_config.yaml
ln -sf /app/config/vibe_router.py /app/vibe_router.py

# Start LiteLLM
exec python3 -m litellm --config /app/litellm_config.yaml --port 4000 --detailed_debug
