#!/bin/bash
set -e

# ==========================================
# LiteLLM Vibe Router - Deployment Script
# ==========================================

echo "========================================"
echo "LiteLLM Intelligent Router Deployment"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Check prerequisites
print_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed"
    exit 1
fi

print_success "Docker and Docker Compose are installed"

# Step 2: Initialize submodules
print_info "Initializing submodules..."
git submodule update --init --recursive
print_success "Submodules initialized"

# Step 3: Check required files
print_info "Checking required files..."

required_files=("config_final.yaml" "vibe_router.py" "docker-compose.yml" "test_route.py" "cliproxyapi.template.yaml")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file missing: $file"
        exit 1
    fi
done

if [ ! -d "CLIProxyAPI" ]; then
    print_error "Required directory missing: CLIProxyAPI (submodule)"
    exit 1
fi

print_success "All required files present"

if [ -f ".env" ]; then
    print_info "Loading environment variables from .env..."
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

if [ -z "${LITELLM_MASTER_KEY:-}" ]; then
    print_error "LITELLM_MASTER_KEY is not set in .env"
    exit 1
fi

if [ -z "${CHAT_AUTO_API_KEY:-}" ]; then
    print_error "CHAT_AUTO_API_KEY is not set in .env"
    exit 1
fi

if [ -z "${CLIPROXY_MANAGEMENT_KEY:-}" ]; then
    print_error "CLIPROXY_MANAGEMENT_KEY is not set in .env"
    exit 1
fi

if [ ! -f "cliproxyapi.template.yaml" ]; then
    print_error "Required template missing: cliproxyapi.template.yaml"
    exit 1
fi

print_info "Generating CLIProxyAPI configuration from template..."
python3 - <<'PY'
from pathlib import Path
import os

path = Path("cliproxyapi.template.yaml")
dest = Path("cliproxyapi.config.yaml")
chat_key = os.environ.get("CHAT_AUTO_API_KEY", "").strip()
mgmt_key = os.environ.get("CLIPROXY_MANAGEMENT_KEY", "").strip()

if not chat_key:
    raise SystemExit("CHAT_AUTO_API_KEY is required")
if not mgmt_key:
    raise SystemExit("CLIPROXY_MANAGEMENT_KEY is required")

content = path.read_text()
if "{{CHAT_AUTO_API_KEY}}" not in content:
    raise SystemExit("Template is missing {{CHAT_AUTO_API_KEY}} placeholder")
if "{{CLIPROXY_MANAGEMENT_KEY}}" not in content:
    raise SystemExit("Template is missing {{CLIPROXY_MANAGEMENT_KEY}} placeholder")

content = content.replace("{{CHAT_AUTO_API_KEY}}", chat_key)
content = content.replace("{{CLIPROXY_MANAGEMENT_KEY}}", mgmt_key)
dest.write_text(content)
PY
print_success "CLIProxyAPI config generated"

# Step 4: Stop existing containers
print_info "Stopping existing containers..."
docker-compose down 2>/dev/null || docker compose down 2>/dev/null || true
print_success "Existing containers stopped"

# Step 5: Start services
print_info "Starting LiteLLM proxy and Redis..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
else
    docker compose up -d
fi

print_success "Services started"

# Step 6: Wait for services to be ready
print_info "Waiting for services to initialize (15 seconds)..."
sleep 15

# Step 7: Check service health
print_info "Checking service health..."

# Check Redis
if docker exec litellm-vibe-redis redis-cli ping | grep -q "PONG"; then
    print_success "Redis is healthy"
else
    print_error "Redis is not responding"
    docker logs litellm-vibe-redis --tail 20
    exit 1
fi

# Check LiteLLM proxy
if curl -s http://localhost:4000/health > /dev/null 2>&1; then
    print_success "LiteLLM proxy is healthy"
else
    print_error "LiteLLM proxy is not responding"
    docker logs litellm-vibe-router --tail 50
    exit 1
fi

# Step 8: Verify plugin loading
print_info "Checking plugin logs..."
sleep 2

if docker logs litellm-vibe-router 2>&1 | grep -q "VIBE-ROUTER"; then
    print_success "Plugin loaded successfully!"
    echo ""
    echo "Plugin loading messages:"
    docker logs litellm-vibe-router 2>&1 | grep "VIBE-ROUTER" | head -10
else
    print_error "Plugin not loaded - check logs"
    docker logs litellm-vibe-router --tail 50
    exit 1
fi

# Step 9: List available models
print_info "Fetching available models..."
echo ""
curl -s -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
    http://localhost:4000/v1/models | python3 -m json.tool | grep '"id"' || print_error "Failed to fetch models"

# Step 10: Summary
echo ""
echo "========================================"
print_success "Deployment Complete!"
echo "========================================"
echo ""
echo "Services:"
echo "  - LiteLLM Proxy: http://localhost:4000"
echo "  - CLIProxyAPI: http://localhost:8317"
echo "  - Redis: localhost:6379"
echo ""
echo "Virtual Models:"
echo "  - auto-chat   (routes to pool-chat-mini or pool-chat-standard)"
echo "  - auto-codex  (routes to pool-codex-mini or pool-codex-heavy)"
echo "  - auto-claude (routes to pool-claude-haiku or pool-claude-sonnet)"
echo ""
echo "Next Steps:"
echo "  1. Run tests: python3 test_route.py"
echo "  2. View logs: docker logs -f litellm-vibe-router"
echo "  3. Test routing: curl -X POST http://localhost:4000/v1/chat/completions \\" 
echo "                     -H 'Authorization: Bearer ${LITELLM_MASTER_KEY}' \\" 
echo "                     -H 'Content-Type: application/json' \\"
echo "                     -d '{\"model\": \"auto-chat\", \"messages\": [{\"role\": \"user\", \"content\": \"hi\"}]}'"  
echo ""
