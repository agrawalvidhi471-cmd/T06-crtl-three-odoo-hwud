#!/usr/bin/env python3
import time
import random
import argparse
import requests
from datetime import datetime, timezone

ODOO_API_URL = "http://localhost:8069/api/v1/telemetry/ingest"
API_KEY = "sec_live_default_secret_key"


def generate_reading(device_id: str, lot_name: str, scenario: str, current_temp: float):
    if scenario == "normal":
        temp = max(2.5, min(7.5, current_temp + random.uniform(-0.3, 0.3)))
    elif scenario == "spike":
        temp = current_temp + random.uniform(0.5, 1.2)
    elif scenario == "freeze":
        temp = current_temp - random.uniform(0.4, 0.8)
    else:
        temp = 4.5

    return {
        "device_id": device_id,
        "lot_name": lot_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": round(temp, 2),
        "humidity": round(random.uniform(45.0, 55.0), 1),
        "battery_level": round(random.uniform(85.0, 99.0), 1),
        "latitude": 48.8566 + random.uniform(-0.01, 0.01),
        "longitude": 2.3522 + random.uniform(-0.01, 0.01)
    }, temp


def main():
    parser = argparse.ArgumentParser(description="Cold Chain IoT Stream Simulator")
    parser.add_argument("--lot", default="LOT-2026-001", help="Target Stock Lot Name")
    parser.add_argument("--device", default="DEV-LOGGER-01", help="Device Identifier")
    parser.add_argument("--interval", type=int, default=2, help="Seconds between pings")
    parser.add_argument("--scenario", choices=["normal", "spike", "freeze"], default="normal")
    args = parser.parse_args()

    print(f"[*] Starting telemetry streamer for Lot: {args.lot} | Device: {args.device}")
    print(f"[*] Mode: {args.scenario.upper()} | Target: {ODOO_API_URL}")

    current_temp = 4.5
    headers = {"Content-Type": "application/json"}

    while True:
        reading, current_temp = generate_reading(args.device, args.lot, args.scenario, current_temp)
        
        # Standard Odoo JSON-RPC envelope
        json_rpc_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "api_key": API_KEY,
                "readings": [reading]
            },
            "id": random.randint(1, 100000)
        }

        try:
            response = requests.post(ODOO_API_URL, json=json_rpc_payload, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                res = data.get("result", {})
                print(f"[+] Sent: {reading['temperature']}°C | Result: {res.get('status')} (Inserted: {res.get('inserted_count')})")
            else:
                print(f"[-] HTTP Error {response.status_code}: {response.text}")
        except requests.exceptions.ConnectionError:
            print("[-] Connection failed. Is Odoo running on localhost:8069?")
        except Exception as e:
            print(f"[-] Unexpected error: {e}")

        time.sleep(args.interval)


if __name__ == "__main__":
    main()