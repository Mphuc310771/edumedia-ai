"""Verify AgentSys locally. Uses MEDIA_PROVIDER=memory — does not call AWS."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
KEY = "agentsys-dev-secret-key-2026"


def request(method: str, path: str, body: dict | None = None, api_key: str = KEY):
    payload = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=payload,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def main() -> int:
    code, health = request("GET", "/health")
    assert code == 200 and health["provider"] == "memory", health
    print("1. health OK, provider=memory (no AWS credit)")

    code, items = request("GET", "/api/v1/media/items")
    assert code == 200 and len(items) >= 6, items
    print(f"2. catalog OK, {len(items)} items")

    code, query = request(
        "POST",
        "/api/v1/media/agent/query",
        {"user_query": "Tìm đoạn thầy dặn thi cuối kỳ"},
    )
    assert code == 200 and query["results"], query
    names = [item["filename"] for item in query["results"]]
    assert any("AUD" in name or "mp3" in name for name in names), names
    print(f"3. exam-tip query OK -> {names[:3]}")

    code, pets = request(
        "POST",
        "/api/v1/media/agent/query",
        {"user_query": "Tim anh cho long vang"},
    )
    assert code == 200 and any(item["category"] == "pets" for item in pets["results"]), pets
    print("4. unaccented pet query OK")

    code, _ = request("POST", "/api/v1/media/agent/query", {"user_query": "x"}, api_key="wrong")
    assert code == 401, code
    print("5. invalid API key -> 401 OK")

    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print("FAILED:", exc)
        raise SystemExit(1)
    except urllib.error.URLError:
        print("API is not running. Start: python -m uvicorn apps.api.main:app --port 8000")
        raise SystemExit(1)
    except Exception:
        print("FAILED", file=sys.stderr)
        raise
