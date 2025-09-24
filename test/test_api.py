"""API smoke tests for the EOSC service catalogue demonstrator."""

from __future__ import annotations

from typing import Iterable

from fastapi.testclient import TestClient
from jsonschema import validate

from api.app.main import app

client = TestClient(app)


def _iter_sample_services(limit: int = 5) -> Iterable[dict]:
    """Return a handful of service bundles for schema validation."""
    payload = client.get("/api/v1/services", params={"quantity": limit}).json()
    assert payload["items"], "Expected at least one service bundle in the response"
    return payload["items"]


def test_health_endpoint() -> None:
    """The health check should report an OK status."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_schema_endpoint() -> None:
    """The schema endpoint should expose the EOSC bundle definition."""
    response = client.get("/api/v1/schema")
    assert response.status_code == 200
    schema = response.json()
    assert schema["title"] == "EOSC Service Bundle"
    # Validate a few bundles against the retrieved schema.
    for bundle in _iter_sample_services():
        validate(instance=bundle, schema=schema)


def test_single_service_lookup() -> None:
    """Fetching a known SURF bundle should return the expected identifier."""
    response = client.get("/api/v1/services/surf/surf-research-cloud")
    assert response.status_code == 200
    body = response.json()
    assert body["service"]["id"] == "surf/surf-research-cloud"


def test_keyword_filtering() -> None:
    """Keyword filtering should return only services containing the term."""
    response = client.get("/api/v1/services", params={"keyword": "cloud", "quantity": 10})
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"], "Expected keyword search to return results"
    keyword = "cloud"
    for bundle in payload["items"]:
        text = " ".join(
            [
                bundle["service"].get("name", ""),
                bundle["service"].get("description", ""),
                bundle["service"].get("tagline", ""),
                " ".join(bundle["service"].get("tags", [])),
            ]
        ).casefold()
        assert keyword in text
