#!/bin/bash
# Quick Start Guide - Execute this file for instant setup

cat << 'EOF'

╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║       LiteLLM Intelligent Router - Quick Start Guide          ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

This implementation solves the following problems:

1. ✓ Virtual models (auto-chat, auto-codex, auto-claude) pass validation
2. ✓ Plugin intercepts BEFORE router resolution
3. ✓ Complexity-based routing to physical pools
4. ✓ Detailed logging for debugging
5. ✓ Fallback routing if plugin fails

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Files Created:

  Core Implementation:
    ✓ vibe_router.py        - Intelligent routing plugin
    ✓ config_final.yaml     - LiteLLM configuration
    ✓ docker-compose.yml    - Docker deployment

  Testing & Verification:
    ✓ test_route.py         - Comprehensive test suite
    ✓ verify.py             - Quick health check
    ✓ deploy.sh             - Automated deployment

  Documentation:
    ✓ README.md             - Full documentation
    ✓ SUMMARY.md            - Implementation summary
    ✓ QUICKSTART.sh         - This guide

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 DEPLOYMENT OPTIONS:

Option 1: Automated Deployment (Recommended)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ ./deploy.sh up

  Upgrade all container apps:
  $ ./deploy.sh update

Option 2: Manual Deployment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ docker-compose down
  $ docker-compose up -d
  $ python3 verify.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧪 TESTING:

Step 1: Quick Verification (No API Calls)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ python3 verify.py
  
  This checks:
  - Containers running
  - Files mounted
  - PYTHONPATH set
  - Plugin loaded

Step 2: Comprehensive Test Suite
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ python3 test_route.py
  
  This tests:
  - Simple → Mini routing
  - Complex → Standard routing
  - All 3 virtual models

Step 3: Manual Test
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ curl -X POST http://localhost:4000/v1/chat/completions \
      -H "Authorization: Bearer sk-vibe-master-123" \
      -H "Content-Type: application/json" \
      -d '{"model": "auto-chat", "messages": [{"role": "user", "content": "hi"}]}'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 MONITORING:

View Real-Time Routing Decisions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ docker logs -f litellm-vibe-router 2>&1 | grep "ROUTING DECISION"

View All Plugin Logs:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ docker logs -f litellm-vibe-router 2>&1 | grep VIBE-ROUTER

Check Success/Failure:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ docker logs litellm-vibe-router 2>&1 | grep -E "SUCCESS|FAILURE"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 ROUTING BEHAVIOR:

Virtual Model → Physical Pools:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  auto-chat:
    Simple   → pool-chat-mini      (gpt-5-mini)
    Complex  → pool-chat-standard  (gpt-5)

  auto-codex:
    Simple   → pool-codex-mini     (gpt-5.1-codex-mini)
    Complex  → pool-codex-heavy    (gpt-5.2-codex)

  auto-claude:
    Simple   → pool-claude-haiku   (claude-haiku-4-5)
    Complex  → pool-claude-sonnet  (claude-sonnet-4-5)

Complexity Threshold: 50 points
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Score < 50  → Simple route (Mini/Haiku)
  Score ≥ 50  → Complex route (Standard/Sonnet)

Scoring Factors:
  + Message length (up to 200)
  - Simple keywords: ls, cat, hi, hello (-100 each)
  + Complex keywords: implement, analyze (+150 each)
  + Code blocks (+100)
  + Multiple sentences (+50)
  + Long conversations (+30)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 CUSTOMIZATION:

Edit Routing Behavior:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  File: vibe_router.py
  
  1. Adjust complexity threshold:
     COMPLEXITY_THRESHOLD = 50  # Line ~154
  
  2. Add custom keywords:
     self.simple_indicators = {...}    # Line ~47
     self.complex_indicators = {...}   # Line ~55
  
  3. Modify scoring logic:
     _calculate_complexity() method    # Line ~62

Change Model Mappings:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  File: vibe_router.py
  
  self.route_map = {
      "auto-chat": ("pool-chat-mini", "pool-chat-standard"),
      "your-auto": ("your-mini-pool", "your-heavy-pool"),
  }

Add New Physical Pools:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  File: config_final.yaml
  
  model_list:
    - model_name: your-mini-pool
      litellm_params:
        model: "provider/model-name"
        api_base: ${NEW_API_BASE}
        api_key: ${NEW_API_KEY}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🐛 TROUBLESHOOTING:

Plugin not loading?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ docker exec litellm-vibe-router python3 -c "import vibe_router; print('OK')"
  $ docker exec litellm-vibe-router env | grep PYTHONPATH

Model not found?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Check all physical pools exist in config_final.yaml

Connection refused?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ curl http://localhost:3000/v1/models  # Check New API
  $ docker exec litellm-vibe-router ping -c 1 host.docker.internal

Full logs:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ docker logs litellm-vibe-router --tail 100

Restart services:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  $ docker-compose down && docker-compose up -d

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 DOCUMENTATION:

  README.md    - Full user guide with examples
  SUMMARY.md   - Technical implementation summary
  
  Read online:
  $ cat README.md
  $ cat SUMMARY.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎉 QUICK SUCCESS CHECK:

Run this command sequence:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Deploy:   ./deploy.sh
  2. Verify:   python3 verify.py
  3. Test:     python3 test_route.py
  4. Monitor:  docker logs -f litellm-vibe-router 2>&1 | grep ROUTING

If all pass, system is production-ready! ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

# Ask user what they want to do
echo ""
read -p "Do you want to deploy now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting deployment..."
    ./deploy.sh
else
    echo "Deployment skipped. Run './deploy.sh' when ready."
fi
