# EOSC Service Catalogue Demonstrator API

This repository hosts a minimal viable API that showcases how an EOSC Node can expose its service catalogue following the Appendix A guidelines. The demonstrator is intentionally lightweight: it serves a static list of service bundles, implements the prescribed query parameters, and publishes an OpenAPI document together with an interactive Swagger UI.

## Requirements

- Python 3.10 or newer
- Optional: a virtual environment tool such as `venv` or `conda`

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
```

## Running the API

Start the API with Uvicorn:

```bash
uvicorn api.app.main:app --reload
```

The server exposes:

- `GET /healthz` – liveness check
- `GET /api/v1/services` – list services with filters
- `GET /api/v1/services/{prefix}/{suffix}` – retrieve a single service bundle
- `GET /api/v1/openapi.json` – OpenAPI specification
- `GET /api/v1/docs` – Swagger UI
- `GET /api/v1/redoc` – ReDoc UI

## Query parameters

`GET /api/v1/services` implements the filters defined in Appendix A. Examples:

```bash
curl 'http://localhost:8000/api/v1/services?active=true&keyword=cloud&quantity=5'

curl 'http://localhost:8000/api/v1/services?from=1&quantity=2&order=desc&sort=abbreviation'
```

- `active` (boolean) – restrict to active services
- `keyword` (string) – case-insensitive match against name, description, tagline, and tags
- `from` (integer, alias `skip`) – zero-based start offset
- `quantity` (integer) – number of results to return (1–100)
- `order` (`asc` or `desc`) – sort direction
- `sort` (`name`, `abbreviation`, `lifeCycleStatus`) – field used for ordering

Responses include the filtered `items` array plus pagination metadata (`total`, `from`, `quantity`, `order`, `sort`).

## Demonstrator data set

The static data backing the API lives in `api/data/services.json`. Each bundle models a realistic subset of the Appendix B schema and can be replaced with harvested records when integrating with production catalogues. The data set is validated on startup against `eosc_service_catalogue.schema.json`; any schema violations will stop the server with a clear error message.

In addition, `api/data/surf-services.json` contains 55 service bundles harvested from the public SURF service catalogue. Both files are loaded and exposed through the same API, so you can experiment with a mixed dataset spanning handcrafted examples and real-world records.

## Development notes

- Update `api/data/services.json` to plug in data exported from an EOSC node catalogue.
- Extend `_ALLOWED_SORT_FIELDS` in `api/app/main.py` if additional sorting fields are needed.

## License

This project is distributed under the terms of the MIT License. See [`LICENSE`](LICENSE).

## Citation

If you reuse this demonstrator, please cite it using the metadata in [`CITATION.cff`](CITATION.cff).
