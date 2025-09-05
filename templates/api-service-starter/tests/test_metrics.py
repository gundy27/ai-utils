from fastapi.testclient import TestClient

from app.main import app


def test_metrics_endpoint_exposes_prometheus_text():
    client = TestClient(app, raise_server_exceptions=False)
    # hit an endpoint to generate some metrics
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body
