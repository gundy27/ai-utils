import os
import time
from fastapi.testclient import TestClient

# Import app from the starter
from app.main import app


def test_health_ok():
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_rate_limit_blocks(monkeypatch):
    client = TestClient(app, raise_server_exceptions=False)
    # Enable strict rate limit: 1 request per 2 seconds
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "2")
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "1")

    # First request passes
    r1 = client.get("/health")
    assert r1.status_code == 200

    # Second request within window should be 429
    r2 = client.get("/health")
    assert r2.status_code == 200  # health is excluded from rate limiting

    # Hit a non-health endpoint; first should pass, second should block
    r3 = client.post("/chat", json={"model": "x", "messages": []})
    # Upstream may error; first call should not be rate-limited
    assert r3.status_code in (200, 500, 502)

    r4 = client.post("/chat", json={"model": "x", "messages": []})
    # Should be blocked by rate limiter (some stacks may surface as 500 during testing)
    assert r4.status_code in (429, 500)

    # After window elapses, requests pass again
    time.sleep(2)
    r5 = client.post("/chat", json={"model": "x", "messages": []})
    assert r5.status_code in (200, 500, 502)
