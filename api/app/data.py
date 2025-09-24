"""Helpers for loading demonstrator data sets."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from jsonschema import Draft202012Validator, exceptions as jsonschema_exceptions

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "services.json"
_SCHEMA_FILE = Path(__file__).resolve().parent.parent.parent / "eosc_service_catalogue.schema.json"

with _SCHEMA_FILE.open("r", encoding="utf-8") as schema_handle:
    _SERVICE_BUNDLE_SCHEMA = json.load(schema_handle)

_VALIDATOR = Draft202012Validator(_SERVICE_BUNDLE_SCHEMA)


def _validate_service_bundles(bundles: List[Dict[str, Any]]) -> None:
    """Raise ValueError if any bundle violates the EOSC schema."""
    for index, bundle in enumerate(bundles):
        try:
            _VALIDATOR.validate(bundle)
        except jsonschema_exceptions.ValidationError as error:
            raise ValueError(f"Bundle at index {index} fails schema validation: {error.message}") from error


@lru_cache(maxsize=1)
def load_service_bundles() -> List[Dict[str, Any]]:
    """Return the service bundles included with the demonstrator."""
    with _DATA_FILE.open("r", encoding="utf-8") as handle:
        bundles: List[Dict[str, Any]] = json.load(handle)
    _validate_service_bundles(bundles)
    return bundles
