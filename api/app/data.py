"""Data access helpers for the EOSC service catalogue demonstrator."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

# The demonstrator ships with multiple JSON fixtures. They all live under this
# directory so we can iterate and validate them in a uniform way.
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATA_FILES: Iterable[str] = ("services.json",)
_SCHEMA_FILE = _DATA_DIR / "eosc_service_catalogue.schema.json"

# Load the official EOSC service bundle schema once so that we can both expose
# it via the API and reuse it for local validation. The file is plain JSON, so
# we can parse it even when the optional ``jsonschema`` dependency is missing.
with _SCHEMA_FILE.open("r", encoding="utf-8") as schema_handle:
    _SERVICE_BUNDLE_SCHEMA: Dict[str, Any] = json.load(schema_handle)

try:  # Optional dependency: only required when we want to validate the bundles.
    from jsonschema import Draft202012Validator, exceptions as jsonschema_exceptions
except ImportError as exc:  # pragma: no cover - handled gracefully at runtime
    Draft202012Validator = None  # type: ignore[assignment]
    jsonschema_exceptions = None  # type: ignore[assignment]
    _VALIDATOR = None
    _VALIDATION_IMPORT_ERROR: Exception | None = exc
else:
    _VALIDATION_IMPORT_ERROR = None
    _VALIDATOR = Draft202012Validator(_SERVICE_BUNDLE_SCHEMA)


def _ensure_validator() -> None:
    """Fail with guidance when jsonschema is absent."""
    if _VALIDATOR is None:
        raise RuntimeError(
            "jsonschema is required to validate service bundles. "
            "Install it with `pip install -r api/requirements.txt`."
        ) from _VALIDATION_IMPORT_ERROR


def _validate_service_bundles(source: Path, bundles: List[Dict[str, Any]]) -> None:
    """Validate every bundle in ``source`` against the EOSC schema."""
    _ensure_validator()
    assert _VALIDATOR is not None  # for type-checkers
    try:
        for index, bundle in enumerate(bundles):
            _VALIDATOR.validate(bundle)
    except jsonschema_exceptions.ValidationError as error:  # type: ignore[attr-defined]
        raise ValueError(
            f"Bundle from {source.name} at index {index} fails schema validation: {error.message}"
        ) from error


def _load_one(path: Path) -> List[Dict[str, Any]]:
    """Load and validate a single JSON fixture file."""
    with path.open("r", encoding="utf-8") as handle:
        bundles: List[Dict[str, Any]] = json.load(handle)
    _validate_service_bundles(path, bundles)
    return bundles


def get_service_schema() -> Dict[str, Any]:
    """Return the EOSC service bundle JSON schema."""
    return _SERVICE_BUNDLE_SCHEMA


@lru_cache(maxsize=1)
def load_service_bundles() -> List[Dict[str, Any]]:
    """Return all bundled services, aggregating every JSON fixture."""
    bundles: List[Dict[str, Any]] = []
    for filename in _DATA_FILES:
        path = _DATA_DIR / filename
        if not path.exists():
            continue
        bundles.extend(_load_one(path))
    return bundles
