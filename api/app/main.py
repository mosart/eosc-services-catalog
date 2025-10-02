"""FastAPI application exposing the EOSC service catalogue demonstrator."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse

from .data import (
    LATEST_VERSION,
    SUPPORTED_VERSIONS,
    get_service_schema,
    iter_service_bundles,
)

# Configure the FastAPI application. The latest catalogue version drives the
# default documentation URLs so that users land on the newest API first.
app = FastAPI(
    title="EOSC Service Catalogue Demonstrator",
    version="0.3.0",
    description=(
        "Reference implementation of the EOSC service catalogue API as described "
        "in Appendix A of the federation guidelines. Multiple catalogue versions "
        "are exposed so clients can migrate at their own pace."
    ),
    openapi_url=f"/api/{LATEST_VERSION}/openapi.json",
    docs_url=f"/api/{LATEST_VERSION}/docs",
    redoc_url=f"/api/{LATEST_VERSION}/redoc",
)

_ALLOWED_SORT_FIELDS = {"name", "abbreviation", "lifeCycleStatus"}


def _normalise(text: Optional[str]) -> str:
    """Return a case-folded version of ``text`` for insensitive comparisons."""
    return (text or "").casefold()


def _service_iterator(version: str) -> Iterable[Dict[str, Any]]:
    """Yield the loaded service bundles for ``version``."""
    yield from iter_service_bundles(version)


def _get_service_bundle_or_404(version: str, prefix: str, suffix: str) -> Dict[str, Any]:
    """Return the requested service bundle or raise a 404."""
    service_id = f"{prefix}/{suffix}"
    for bundle in _service_iterator(version):
        service = bundle.get("service", {})
        if service.get("id") == service_id:
            return bundle
    raise HTTPException(status_code=404, detail="Service not found")


def _list_services_impl(
    version: str,
    active: Optional[bool],
    keyword: Optional[str],
    skip: int,
    quantity: int,
    order: str,
    sort: str,
) -> Dict[str, Any]:
    """Core implementation shared by the versioned service list endpoints."""
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
    for bundle in _service_iterator(version):
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
        "version": version,
    }


def _create_version_router(version: str) -> APIRouter:
    router = APIRouter(prefix=f"/api/{version}")

    @router.get("/services/{prefix}/{suffix}", tags=["services"])
    def get_service(prefix: str, suffix: str) -> Dict[str, Any]:
        return _get_service_bundle_or_404(version, prefix, suffix)

    @router.get("/services", tags=["services"])
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
        return _list_services_impl(version, active, keyword, skip, quantity, order, sort)

    @router.get("/schema", tags=["metadata"])
    def get_schema() -> Dict[str, Any]:
        return get_service_schema(version)

    return router


for _version in SUPPORTED_VERSIONS:
    app.include_router(_create_version_router(_version))


@app.get("/api/services/{prefix}/{suffix}", tags=["services"])
def get_service_latest(prefix: str, suffix: str) -> Dict[str, Any]:
    """Shortcut for the latest catalogue version."""
    return _get_service_bundle_or_404(LATEST_VERSION, prefix, suffix)


@app.get("/api/services", tags=["services"])
def list_services_latest(
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
    return _list_services_impl(LATEST_VERSION, active, keyword, skip, quantity, order, sort)


@app.get("/api/schema", tags=["metadata"])
def get_schema_latest() -> Dict[str, Any]:
    """Expose the latest EOSC service bundle schema."""
    return get_service_schema(LATEST_VERSION)


@app.get("/api/versions", tags=["metadata"])
def list_versions() -> Dict[str, Any]:
    """List catalogue versions exposed by this API."""
    return {"latest": LATEST_VERSION, "available": list(SUPPORTED_VERSIONS)}


@app.get("/", include_in_schema=False)
def redirect_to_docs() -> RedirectResponse:
    """Send browsers landing on the root URL straight to the Swagger UI."""
    return RedirectResponse(url=f"/api/{LATEST_VERSION}/docs", status_code=307)


@app.get("/healthz", tags=["health"])
def health_check() -> Dict[str, str]:
    """Return a simple health indicator."""
    return {"status": "ok"}


def _custom_openapi() -> Dict[str, Any]:
    """Augment FastAPI's autogenerated document with our bundle schemas."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    components = openapi_schema.setdefault("components", {}).setdefault("schemas", {})

    for version in SUPPORTED_VERSIONS:
        suffix = version.upper()
        bundle_component = f"ServiceBundle{suffix}"
        list_component = f"ServiceBundleList{suffix}"

        components.setdefault(bundle_component, get_service_schema(version))
        components.setdefault(
            list_component,
            {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"$ref": f"#/components/schemas/{bundle_component}"},
                    },
                    "total": {"type": "integer"},
                    "from": {"type": "integer"},
                    "quantity": {"type": "integer"},
                    "order": {"type": "string"},
                    "sort": {"type": "string"},
                    "version": {"type": "string"},
                },
            },
        )

    paths = openapi_schema.get("paths", {})

    for version in SUPPORTED_VERSIONS:
        suffix = version.upper()
        list_component = f"ServiceBundleList{suffix}"
        bundle_component = f"ServiceBundle{suffix}"

        list_path = f"/api/{version}/services"
        detail_path = f"/api/{version}/services/{{prefix}}/{{suffix}}"

        if list_path in paths:
            paths[list_path].setdefault("get", {}).setdefault("responses", {}).setdefault(
                "200",
                {
                    "description": f"Service bundles matching the provided filters for {version}",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{list_component}"}
                        }
                    },
                },
            )

        if detail_path in paths:
            paths[detail_path].setdefault("get", {}).setdefault("responses", {}).setdefault(
                "200",
                {
                    "description": "Service bundle",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{bundle_component}"}
                        }
                    },
                },
            )

    latest_suffix = LATEST_VERSION.upper()
    latest_list_component = f"ServiceBundleList{latest_suffix}"
    latest_bundle_component = f"ServiceBundle{latest_suffix}"

    if "/api/services" in paths:
        paths["/api/services"].setdefault("get", {}).setdefault("responses", {}).setdefault(
            "200",
            {
                "description": "Service bundles matching the provided filters",
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{latest_list_component}"}
                    }
                },
            },
        )

    if "/api/services/{prefix}/{suffix}" in paths:
        paths["/api/services/{prefix}/{suffix}"].setdefault("get", {}).setdefault(
            "responses", {}
        ).setdefault(
            "200",
            {
                "description": "Service bundle",
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{latest_bundle_component}"}
                    }
                },
            },
        )

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = _custom_openapi
