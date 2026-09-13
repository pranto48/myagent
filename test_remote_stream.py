# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
import urllib.request
import json
import sys

print("--- Testing MyAgent Backend SSE Stream ---")
payload = {
    "session_id": "test_verification",
    "prompt": "হ্যালো! পাইথনে একটি ফিবোনাচ্চি ফাংশন লিখে দেখাও।",
    "history": [],
    "use_memory": False
}

req = urllib.request.Request(
    "http://127.0.0.1:8008/api/chat/stream",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        print("HTTP Status:", resp.status)
        collected_tokens = []
        for i, line in enumerate(resp):
            line_str = line.decode("utf-8").strip()
            if line_str.startswith("data: "):
                data_json = json.loads(line_str[6:])
                if data_json.get("type") == "token":
                    collected_tokens.append(data_json.get("token", ""))
            if len(collected_tokens) > 40:
                break
        print("Generated text preview:")
        print("".join(collected_tokens)[:300])
        print("\n[SUCCESS] Streaming SSE pipeline is functioning smoothly!")
except Exception as e:
    print("[ERROR]", e)
    sys.exit(1)
