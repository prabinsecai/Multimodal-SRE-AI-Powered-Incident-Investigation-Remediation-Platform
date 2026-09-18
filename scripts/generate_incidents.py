import argparse
import os
import sys
import requests

def run():
    parser = argparse.ArgumentParser(description="Generate demo SRE incidents and trigger AI investigation")
    parser.add_argument("--scenario", choices=["database-timeout", "redis-failure", "k8s-crashloop"], default="database-timeout")
    parser.add_argument("--api-url", default=os.getenv("API_URL", "http://localhost:8000"))
    args = parser.parse_args()

    base = args.api_url.rstrip("/")
    session = requests.Session()

    print(f"1. Authenticating with {base}...")
    try:
        login_resp = session.post(f"{base}/api/v1/auth/login", json={"email": "admin@local", "password": "admin123"}, timeout=5)
        login_resp.raise_for_status()
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("   ✓ Authenticated successfully.")
    except Exception as e:
        print(f"   ✗ Authentication failed: {e}")
        sys.exit(1)

    print(f"2. Triggering scenario '{args.scenario}'...")
    try:
        scenario_url = f"{base}/api/v1/demo/incidents/{args.scenario}"
        demo_resp = session.post(scenario_url, headers=headers, timeout=10)
        demo_resp.raise_for_status()
        inc_data = demo_resp.json()
        incident_id = inc_data["incident_id"]
        print(f"   ✓ Created incident #{incident_id} ({inc_data.get('service', 'unknown')})")
    except Exception as e:
        print(f"   ✗ Scenario generation failed: {e}")
        sys.exit(1)

    print(f"3. Triggering SRE AI Investigation for incident #{incident_id}...")
    try:
        inv_resp = session.post(f"{base}/api/v1/incidents/{incident_id}/investigate", headers=headers, timeout=30)
        inv_resp.raise_for_status()
        inv_data = inv_resp.json()
        rca = inv_data.get("structured_investigation", {}).get("root_cause", {})
        print("   ✓ Investigation completed successfully:")
        print(f"     - Root Cause: {rca.get('title')}")
        print(f"     - Confidence: {int(rca.get('confidence', 0)*100)}%")
        print(f"     - Recommended Action: {inv_data.get('remediation', {}).get('action')}")
    except Exception as e:
        print(f"   ✗ Investigation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
