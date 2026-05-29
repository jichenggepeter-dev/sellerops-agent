from __future__ import annotations


def test_request_id_header_is_returned(client) -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "test-request-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"
