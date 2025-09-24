"""FastAPI application exposing a demonstrator EOSC service catalogue."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from fastapi import FastAPI, HTTPException, Query

from .data import load_service_bundles

app = FastAPI(
    title="EOSC Service Catalogue Demonstrator",
    version="0.1.0",
    description=(
        "Minimal reference implementation of the EOSC service catalogue API "
        "as described in Appendix A of the federation guidelines."
    ),
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

_ALLOWED_SORT_FIELDS = {"name", "abbreviation", "lifeCycleStatus"}


def _normalise(text: Optional[str]) -> str:
    return (text or "").casefold()


def _iter_services() -> Iterable[Dict[str, Any]]:
    yield from load_service_bundles()


@app.get("/healthz", tags=["health"])
def health_check() -> Dict[str, str]:
    """Return a simple health indicator."""
    return {"status": "ok"}


@app.get("/api/v1/services/{prefix}/{suffix}", tags=["services"])
def get_service(prefix: str, suffix: str) -> Dict[str, Any]:
    """Return a single service bundle identified by prefix/suffix."""
    service_id = f"{prefix}/{suffix}"
    for bundle in _iter_services():
        service = bundle.get("service", {})
        if service.get("id") == service_id:
            return bundle
    raise HTTPException(status_code=404, detail="Service not found")


@app.get("/api/v1/services", tags=["services"])
def list_services(
    active: Optional[bool] = Query(None, description="Filter by active flag"),
    keyword: Optional[str] = Query(
        None,
        description="Keyword matched against name, description, tagline, and tags",
    ),
    skip: int = Query(0, alias="from", ge=0, description="Start offset in the result set"),
    quantity: int = Query(
        10,
        alias="quantity",
        ge=1,
        le=100,
        description="Number of results to return",
    ),
    order: str = Query(
        "asc",
        description="Sort order (asc or desc)",
    ),
    sort: str = Query(
        "name",
        description="Field used for ordering",
    ),
) -> Dict[str, Any]:
    """Return service bundles that match the provided filters."""
    sort_field = sort
    if sort_field not in _ALLOWED_SORT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported sort field '{sort_field}'. Allowed: {sorted(_ALLOWED_SORT_FIELDS)}",
        )

    order_value = order.lower()
    if order_value not in {"asc", "desc"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported order value. Allowed: ['asc', 'desc']",
        )

    filtered: List[Dict[str, Any]] = []
    for bundle in _iter_services():
        if active is not None and bundle.get("active") is not active:
            continue

        if keyword:
            svc = bundle.get("service", {})
            haystack = " ".join(
                [
                    svc.get("name", ""),
                    svc.get("description", ""),
                    svc.get("tagline", ""),
                    " ".join(svc.get("tags", [])),
                ]
            )
            if keyword.casefold() not in _normalise(haystack):
                continue

        filtered.append(bundle)

    reverse = order_value == "desc"

    def sort_key(item: Dict[str, Any]) -> Any:
        service = item.get("service", {})
        return _normalise(service.get(sort_field))

    filtered.sort(key=sort_key, reverse=reverse)

    total = len(filtered)
    paginated = filtered[skip : skip + quantity]

    return {
        "items": paginated,
        "total": total,
        "from": skip,
        "quantity": len(paginated),
        "order": order_value,
        "sort": sort_field,
    }
