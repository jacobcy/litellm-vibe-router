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

# Step 2: Check required files
print_info "Checking required files..."

required_files=("config_final.yaml" "vibe_router.py" "docker-compose.yml" "test_route.py")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file missing: $file"
        exit 1
    fi
done

print_success "All required files present"

# Step 3: Stop existing containers
print_info "Stopping existing containers..."
docker-compose down 2>/dev/null || docker compose down 2>/dev/null || true
print_success "Existing containers stopped"

# Step 4: Start services
print_info "Starting LiteLLM proxy and Redis..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
else
    docker compose up -d
fi

print_success "Services started"

# Step 5: Wait for services to be ready
print_info "Waiting for services to initialize (15 seconds)..."
sleep 15

# Step 6: Check service health
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

# Step 7: Verify plugin loading
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

# Step 8: List available models
print_info "Fetching available models..."
echo ""
curl -s -H "Authorization: Bearer sk-vibe-master-123" \
    http://localhost:4000/v1/models | python3 -m json.tool | grep '"id"' || print_error "Failed to fetch models"

# Step 9: Summary
echo ""
echo "========================================"
print_success "Deployment Complete!"
echo "========================================"
echo ""
echo "Services:"
echo "  - LiteLLM Proxy: http://localhost:4000"
echo "  - Redis: localhost:6379"
echo ""
echo "Virtual Models:"
echo "  - chat-auto   (routes to pool-chat-mini or pool-chat-standard)"
echo "  - codex-auto  (routes to pool-codex-mini or pool-codex-heavy)"
echo "  - claude-auto (routes to pool-claude-haiku or pool-claude-sonnet)"
echo ""
echo "Next Steps:"
echo "  1. Run tests: python3 test_route.py"
echo "  2. View logs: docker logs -f litellm-vibe-router"
echo "  3. Test routing: curl -X POST http://localhost:4000/v1/chat/completions \\"
echo "                     -H 'Authorization: Bearer sk-vibe-master-123' \\"
echo "                     -H 'Content-Type: application/json' \\"
echo "                     -d '{\"model\": \"chat-auto\", \"messages\": [{\"role\": \"user\", \"content\": \"hi\"}]}'"
echo ""
