#!/usr/bin/env python3
"""
Quick verification script for LiteLLM router setup
Tests plugin loading without making actual API calls
"""

import subprocess
import sys
import time

def run_command(cmd, description):
    """Run a shell command and return output"""
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✓ SUCCESS")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()[:200]}")
            return True
        else:
            print(f"✗ FAILED (exit code {result.returncode})")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ TIMEOUT")
        return False
    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
        return False

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║       LiteLLM Vibe Router - Quick Verification             ║
╚════════════════════════════════════════════════════════════╝
""")
    
    tests = [
        {
            "cmd": "docker ps | grep litellm-vibe-router",
            "desc": "LiteLLM container running"
        },
        {
            "cmd": "docker ps | grep litellm-vibe-redis",
            "desc": "Redis container running"
        },
        {
            "cmd": "docker exec litellm-vibe-router ls -l /app/vibe_router.py",
            "desc": "Plugin file mounted"
        },
        {
            "cmd": "docker exec litellm-vibe-router ls -l /app/config.yaml",
            "desc": "Config file mounted"
        },
        {
            "cmd": "docker exec litellm-vibe-router env | grep 'PYTHONPATH=/app'",
            "desc": "PYTHONPATH set correctly"
        },
        {
            "cmd": "docker exec litellm-vibe-router python3 -c 'import vibe_router; print(\"Plugin import OK\")'",
            "desc": "Plugin can be imported"
        },
        {
            "cmd": "docker logs litellm-vibe-router 2>&1 | grep 'VIBE-ROUTER' | head -1",
            "desc": "Plugin loading messages in logs"
        },
        {
            "cmd": "curl -s http://localhost:4000/health > /dev/null && echo 'Health check passed'",
            "desc": "Proxy health endpoint responding"
        },
    ]
    
    results = []
    for test in tests:
        result = run_command(test["cmd"], test["desc"])
        results.append((test["desc"], result))
        time.sleep(0.5)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for desc, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {desc}")
    
    print(f"\nResults: {passed}/{total} tests passed\n")
    
    if passed == total:
        print("✓ ALL CHECKS PASSED - System is ready!")
        print("\nNext steps:")
        print("  1. Run full test suite: python3 test_route.py")
        print("  2. View routing logs: docker logs -f litellm-vibe-router 2>&1 | grep VIBE-ROUTER")
        print("  3. Make a test request to see routing in action")
        return 0
    else:
        print("✗ SOME CHECKS FAILED - Review errors above")
        print("\nTroubleshooting:")
        print("  1. Check logs: docker logs litellm-vibe-router")
        print("  2. Restart: docker-compose down && docker-compose up -d")
        print("  3. Verify files: ls -l vibe_router.py config_final.yaml")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nVerification interrupted")
        sys.exit(130)
