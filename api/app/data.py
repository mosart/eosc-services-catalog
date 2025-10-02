"""Data access helpers for the EOSC service catalogue demonstrator."""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

# Directory layout shared by all catalogue fixtures and schemas.
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"

# Supported catalogue versions and their associated resources.
SUPPORTED_VERSIONS: Tuple[str, ...] = ("v1", "v3")
LATEST_VERSION = "v3"

_CATALOGUE_DATA_FILES: Dict[str, Tuple[str, ...]] = {
    "v1": ("v1/surf-services-selection-for-eosc.json",),
    "v3": ("v3/surf-services-selection-for-eosc-v3.json",),
}

_SCHEMA_PATHS: Dict[str, Path] = {
    "v1": _SCHEMA_DIR / "eosc_service_catalogue.schema_v1.json",
    "v3": _SCHEMA_DIR / "eosc_service_catalogue.schema_v3.json",
}

try:  # Optional dependency: only required when we want to validate the bundles.
    from jsonschema import Draft202012Validator, exceptions as jsonschema_exceptions
except ImportError as exc:  # pragma: no cover - handled gracefully at runtime
    Draft202012Validator = None  # type: ignore[assignment]
    jsonschema_exceptions = None  # type: ignore[assignment]
    _VALIDATION_IMPORT_ERROR: Exception | None = exc
else:
    _VALIDATION_IMPORT_ERROR = None

# Cache schemas, validators, and file lists per catalogue version.
_CATALOGUES: Dict[str, Dict[str, Any]] = {}
for version in SUPPORTED_VERSIONS:
    schema_path = _SCHEMA_PATHS[version]
    with schema_path.open("r", encoding="utf-8") as schema_handle:
        schema = json.load(schema_handle)
    data_files = tuple(_DATA_DIR / rel for rel in _CATALOGUE_DATA_FILES[version])
    validator = Draft202012Validator(schema) if Draft202012Validator else None
    _CATALOGUES[version] = {
        "schema": schema,
        "data_files": data_files,
        "validator": validator,
    }


def _assert_supported_version(version: str) -> str:
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f"Unsupported catalogue version '{version}'")
    return version


def _ensure_validator() -> None:
    """Fail with guidance when jsonschema is absent."""
    if Draft202012Validator is None:
        raise RuntimeError(
            "jsonschema is required to validate service bundles. "
            "Install it with `pip install -r api/requirements.txt`."
        ) from _VALIDATION_IMPORT_ERROR


def _validate_service_bundles(
    version: str, source: Path, bundles: List[Dict[str, Any]]
) -> None:
    """Validate every bundle in ``source`` against the EOSC schema for ``version``."""
    catalogue = _CATALOGUES[version]
    validator = catalogue["validator"]
    if validator is None:
        _ensure_validator()
        validator = catalogue["validator"]
        assert validator is not None  # pragma: no cover - guarded by _ensure_validator
    try:
        for index, bundle in enumerate(bundles):
            validator.validate(bundle)
    except jsonschema_exceptions.ValidationError as error:  # type: ignore[union-attr]
        raise ValueError(
            f"Bundle from {source.name} at index {index} fails schema validation: {error.message}"
        ) from error


def _load_one(version: str, path: Path) -> List[Dict[str, Any]]:
    """Load and validate a single JSON fixture file for ``version``."""
    with path.open("r", encoding="utf-8") as handle:
        bundles: List[Dict[str, Any]] = json.load(handle)
    _validate_service_bundles(version, path, bundles)
    return bundles


def get_service_schema(version: str = LATEST_VERSION) -> Dict[str, Any]:
    """Return a deepcopy of the EOSC service bundle JSON schema for ``version``."""
    version = _assert_supported_version(version)
    return copy.deepcopy(_CATALOGUES[version]["schema"])


@lru_cache(maxsize=None)
def load_service_bundles(version: str = LATEST_VERSION) -> List[Dict[str, Any]]:
    """Return all bundled services for ``version``, aggregating every JSON fixture."""
    version = _assert_supported_version(version)
    bundles: List[Dict[str, Any]] = []
    for path in _CATALOGUES[version]["data_files"]:
        if not path.exists():
            continue
        bundles.extend(_load_one(version, path))
    return bundles


def iter_service_bundles(version: str = LATEST_VERSION) -> Iterable[Dict[str, Any]]:
    """Yield bundles for ``version`` without exposing the underlying cache."""
    # Return a generator so callers cannot mutate the cached list in-place.
    for bundle in load_service_bundles(version):
        yield bundle
