"""Helpers for loading demonstrator data sets."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

from jsonschema import Draft202012Validator, exceptions as jsonschema_exceptions

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATA_FILES: Iterable[str] = ("services.json", "surf-services.json")
_SCHEMA_FILE = Path(__file__).resolve().parent.parent.parent / "eosc_service_catalogue.schema.json"

with _SCHEMA_FILE.open("r", encoding="utf-8") as schema_handle:
    _SERVICE_BUNDLE_SCHEMA = json.load(schema_handle)

_VALIDATOR = Draft202012Validator(_SERVICE_BUNDLE_SCHEMA)


def _validate_service_bundles(source: Path, bundles: List[Dict[str, Any]]) -> None:
    """Raise ValueError if any bundle violates the EOSC schema."""
    for index, bundle in enumerate(bundles):
        try:
            _VALIDATOR.validate(bundle)
        except jsonschema_exceptions.ValidationError as error:
            raise ValueError(
                f"Bundle from {source.name} at index {index} fails schema validation: {error.message}"
            ) from error


def _load_one(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        bundles: List[Dict[str, Any]] = json.load(handle)
    _validate_service_bundles(path, bundles)
    return bundles


@lru_cache(maxsize=1)
def load_service_bundles() -> List[Dict[str, Any]]:
    """Return the service bundles included with the demonstrator."""
    bundles: List[Dict[str, Any]] = []
    for filename in _DATA_FILES:
        path = _DATA_DIR / filename
        if not path.exists():
            continue
        bundles.extend(_load_one(path))
    return bundles
