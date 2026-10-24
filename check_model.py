"""
Model availability check (template standard).
Used internally; not part of the scoring flow.
"""
import json
import os
import sys
import urllib.request
import urllib.error


def check_model():
    model = os.environ.get("MODEL", "")
    api_key = os.environ.get("API_KEY", "")
    base_url = os.environ.get("BASE_URL", "https://api.openai.com/v1").rstrip("/")

    if model.startswith("mock/"):
        print(f"Mock model: {model}", flush=True)
        return True

    if not api_key:
        print("ERROR: API_KEY not set", flush=True)
        return False

    try:
        data = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": "Say OK"}],
            "max_tokens": 5,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            print(f"Model check OK: {model}", flush=True)
            return True
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        print(f"Model check FAILED: HTTP {e.code}: {body[:500]}", flush=True)
        return False
    except Exception as e:
        print(f"Model check FAILED: {e}", flush=True)
        return False


if __name__ == "__main__":
    if not check_model():
        sys.exit(1)
