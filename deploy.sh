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

wait_for_http_ok() {
    local url="$1"
    local timeout_seconds="$2"
    local elapsed=0
    while [ "${elapsed}" -lt "${timeout_seconds}" ]; do
        if curl -s "${url}" > /dev/null 2>&1; then
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    return 1
}

COMPOSE_CMD=""
ACTION="up"
SERVICES_CSV=""
SERVICE_FILTER_ENABLED=false

ALLOWED_SERVICES=("litellm" "new-api" "cliproxyapi" "postgres" "redis")
SELECTED_SERVICES=()

get_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        echo "docker compose"
    fi
}

run_compose() {
    ${COMPOSE_CMD} "$@"
}

print_usage() {
    cat <<'EOF'
Usage:
  ./deploy.sh [up|update] [--services litellm,new-api]
  ./deploy.sh --help

Commands:
  up      Stop and recreate services (default)
  update  Pull latest images and force-recreate all services

Options:
  --services  Comma-separated services to operate on.
              Available: litellm,new-api,cliproxyapi,postgres,redis
  -h, --help  Show help message

Examples:
  ./deploy.sh
  ./deploy.sh up
  ./deploy.sh update
  ./deploy.sh up --services litellm,new-api
  ./deploy.sh update --services litellm
EOF
}

is_allowed_service() {
    local service="$1"
    for allowed in "${ALLOWED_SERVICES[@]}"; do
        if [ "${service}" = "${allowed}" ]; then
            return 0
        fi
    done
    return 1
}

parse_services() {
    local raw="$1"
    IFS=',' read -r -a SELECTED_SERVICES <<< "${raw}"
    if [ "${#SELECTED_SERVICES[@]}" -eq 0 ]; then
        print_error "--services cannot be empty"
        exit 1
    fi

    for service in "${SELECTED_SERVICES[@]}"; do
        if ! is_allowed_service "${service}"; then
            print_error "Unsupported service: ${service}"
            print_error "Available services: ${ALLOWED_SERVICES[*]}"
            exit 1
        fi
    done
}

service_selected() {
    local service="$1"
    if [ "${SERVICE_FILTER_ENABLED}" = false ]; then
        return 0
    fi
    for selected in "${SELECTED_SERVICES[@]}"; do
        if [ "${service}" = "${selected}" ]; then
            return 0
        fi
    done
    return 1
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        up|update)
            ACTION="$1"
            ;;
        --services)
            if [ -z "${2:-}" ]; then
                print_error "--services requires a value"
                print_usage
                exit 1
            fi
            SERVICES_CSV="$2"
            SERVICE_FILTER_ENABLED=true
            shift
            ;;
        -h|--help|help)
            print_usage
            exit 0
            ;;
        *)
            print_error "Unsupported argument: $1"
            print_usage
            exit 1
            ;;
    esac
    shift
done

if [ "${SERVICE_FILTER_ENABLED}" = true ]; then
    parse_services "${SERVICES_CSV}"
fi

if [[ "${ACTION}" != "up" && "${ACTION}" != "update" ]]; then
    print_error "Unsupported action: ${ACTION}"
    print_usage
    exit 1
fi

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

COMPOSE_CMD="$(get_compose_cmd)"

print_success "Docker and Docker Compose are installed"

# Step 2: Initialize submodules
print_info "Initializing submodules..."
git submodule update --init --recursive
print_success "Submodules initialized"

# Step 3: Check required files
print_info "Checking required files..."

required_files=("config_final.yaml" "vibe_router.py" "docker-compose.yml" "cliproxyapi.template.yaml")
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
dest = Path("CLIProxyAPI/config.yaml")
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
if [ "${SERVICE_FILTER_ENABLED}" = false ]; then
    print_info "Stopping existing containers..."
    run_compose down 2>/dev/null || true
    print_success "Existing containers stopped"
else
    print_info "Service filter enabled: ${SERVICES_CSV}"
fi

# Clean up legacy standalone container with the same name when managed by compose
if service_selected "new-api" || service_selected "litellm"; then
    if docker ps -a --format '{{.Names}}' | grep -qx 'new-api'; then
        print_info "Removing legacy standalone container: new-api"
        docker rm -f new-api >/dev/null 2>&1 || true
    fi
fi

# Step 5: Pull updates if requested
if [ "${ACTION}" = "update" ]; then
    print_info "Updating all container images..."
    if [ "${SERVICE_FILTER_ENABLED}" = true ]; then
        run_compose pull --ignore-pull-failures "${SELECTED_SERVICES[@]}" || true
    else
        run_compose pull --ignore-pull-failures || true
    fi
    print_success "Image update check completed"
fi

# Step 6: Start services
if [ "${ACTION}" = "update" ]; then
    print_info "Recreating all services with latest images..."
    if [ "${SERVICE_FILTER_ENABLED}" = true ]; then
        run_compose up -d --build --force-recreate "${SELECTED_SERVICES[@]}"
    else
        run_compose up -d --build --force-recreate
    fi
else
    if [ "${SERVICE_FILTER_ENABLED}" = true ]; then
        print_info "Starting selected services: ${SERVICES_CSV}"
    else
        print_info "Starting LiteLLM, New API, CLIProxyAPI, PostgreSQL and Redis..."
    fi
    if [ "${SERVICE_FILTER_ENABLED}" = true ]; then
        run_compose up -d --build "${SELECTED_SERVICES[@]}"
    else
        run_compose up -d --build
    fi
fi

print_success "Services started"

# Step 7: Wait for services to be ready
print_info "Waiting for services to initialize (15 seconds)..."
sleep 15

# Step 8: Check service health
print_info "Checking service health..."

# Check Redis
if service_selected "redis" && docker exec litellm-vibe-redis redis-cli ping | grep -q "PONG"; then
    print_success "Redis is healthy"
elif service_selected "redis"; then
    print_error "Redis is not responding"
    docker logs litellm-vibe-redis --tail 20
    exit 1
fi

# Check LiteLLM proxy
if service_selected "litellm" && wait_for_http_ok "http://localhost:4000/health/liveliness" 90; then
    print_success "LiteLLM proxy is healthy"
elif service_selected "litellm"; then
    print_error "LiteLLM proxy is not responding"
    docker logs litellm-vibe-router --tail 50
    exit 1
fi

# Check New API proxy
if service_selected "new-api" && wait_for_http_ok "http://localhost:3000/" 60; then
    print_success "New API is reachable"
elif service_selected "new-api"; then
    print_error "New API is not responding"
    docker logs new-api --tail 50
    exit 1
fi

# Step 9: Verify plugin loading
if service_selected "litellm"; then
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
fi

# Step 10: List available models
print_info "Fetching available models..."
echo ""
if service_selected "litellm"; then
    curl -s -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
        http://localhost:4000/v1/models | python3 -m json.tool | grep '"id"' || print_error "Failed to fetch models"
else
    print_info "Skipping model listing (litellm not selected)"
fi

# Step 11: Summary
echo ""
echo "========================================"
print_success "Deployment Complete!"
echo "========================================"
echo ""
echo "Services:"
if service_selected "litellm"; then echo "  - LiteLLM Proxy: http://localhost:4000"; fi
if service_selected "new-api"; then echo "  - New API: http://localhost:3000"; fi
if service_selected "cliproxyapi"; then echo "  - CLIProxyAPI: http://localhost:8317"; fi
if service_selected "redis"; then echo "  - Redis: localhost:6379"; fi
if service_selected "postgres"; then echo "  - PostgreSQL: localhost:5432"; fi
echo ""
if service_selected "litellm"; then
    echo "Virtual Models:"
    echo "  - auto-chat   (routes to pool-chat-mini or pool-chat-standard)"
    echo "  - auto-codex  (routes to pool-codex-mini or pool-codex-heavy)"
    echo "  - auto-claude (routes to pool-claude-haiku or pool-claude-sonnet)"
    echo ""
fi
echo "Next Steps:"
echo "  1. Run tests: ./test.sh"
echo "  2. View logs: docker logs -f litellm-vibe-router"
echo "  3. Upgrade all services later: ./deploy.sh update"
echo "  4. Start subset: ./deploy.sh up --services litellm,new-api"
echo "  5. Test routing: curl -X POST http://localhost:4000/v1/chat/completions \\" 
echo "                     -H 'Authorization: Bearer ${LITELLM_MASTER_KEY}' \\" 
echo "                     -H 'Content-Type: application/json' \\"
echo "                     -d '{\"model\": \"auto-chat\", \"messages\": [{\"role\": \"user\", \"content\": \"hi\"}]}'"  
echo ""
