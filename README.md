# EOSC Service Catalogue Demonstrator API

## TL;DR
- FastAPI demo that serves EOSC-compliant service bundles from versioned JSON fixtures (v1 and v3).
- Latest Swagger UI available at `/api/v3/docs` (root URL redirects there automatically); legacy docs remain at `/api/v1/docs`.
- Includes SURF catalogue sample data, scraper, CKAN scheming profile, and pytest suite with schema validation.

## Purpose
Provide a minimal, self-contained example of the API described in Appendix A of *EEN Federating Capabilities for EOSC Service Catalogues*. The project helps EOSC Nodes prototype a compliant service catalogue endpoint without standing up a full backend.

## Features
- FastAPI implementation with side-by-side `/api/v1` and `/api/v3` endpoints, plus latest shortcuts under `/api/services`.
- OpenAPI document enriched with both v1 and v3 EOSC service-bundle JSON schemas.
- Version-aware fixture loader that validates data in `api/data/v*/` against `api/schema/eosc_service_catalogue.schema_*.json`.
- SURF catalogue dataset generator, automated scraper, and CKAN scheming dataset profile for manual data entry.
- Pytest smoke tests that validate API responses against the active schema.

## Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
```

## Configuration
- Data fixtures live in `api/data/v1/` and `api/data/v3/`. Update or add JSON bundles there and extend the `SUPPORTED_VERSIONS` mappings in `api/app/data.py` if you introduce additional versions.
- Optional scraper dependencies are listed in `scraper/requirements.txt`.
- Adjust `_ALLOWED_SORT_FIELDS` or extend the FastAPI routes in `api/app/main.py` to support additional behaviour.

## Usage
### API
Run the development server:
```bash
uvicorn api.app.main:app --reload
```
Browse to `http://127.0.0.1:8000/` to reach the Swagger UI. Key endpoints and sample calls (v3 shown; replace with `v1` for the legacy profile):
- `GET /healthz` – health check
  ```bash
  curl http://127.0.0.1:8000/healthz
  ```
- `GET /api/v3/services` – query catalogue entries
  ```bash
  curl 'http://127.0.0.1:8000/api/v3/services?keyword=cloud&quantity=5'
  ```
  ```python
  import requests

  resp = requests.get(
      'http://127.0.0.1:8000/api/v3/services',
      params={'keyword': 'cloud', 'quantity': 5},
      timeout=10,
  )
  resp.raise_for_status()
  print(resp.json()['items'][0]['service']['name'])
  ```
- `GET /api/v3/services/{prefix}/{suffix}` – fetch a specific bundle
  ```bash
  curl http://127.0.0.1:8000/api/v3/services/surf/surf-research-cloud
  ```
- `GET /api/v3/schema` – retrieve the EOSC schema
  ```bash
  curl http://127.0.0.1:8000/api/v3/schema | jq '.title'
  ```
- `GET /api/v3/openapi.json` – download the OpenAPI document
  ```bash
  curl http://127.0.0.1:8000/api/v3/openapi.json
  ```
Legacy clients can continue to use the `/api/v1/...` endpoints; the project also exposes convenient shortcuts (`/api/services`, `/api/schema`) that always resolve to the latest version (`v3`).

For a production-style run:
```bash
uvicorn api.app.main:app --host 0.0.0.0 --port 8000
```

### Scraper
Harvest the SURF catalogue or regenerate the v3 dataset fixture:
```bash
pip install -r scraper/requirements.txt
python scraper/surf_services_scraper-v3.py --output api/app/data/v3/surf-services-all-v3.json
```
Optional flags:
- `--limit N` – only scrape the first N services
- `--delay S` – pause S seconds between requests

### Tests
Run the smoke tests (requires the virtual environment with JSON schema dependencies):
```bash
source .venv/bin/activate
pytest
```
The suite under `test/` verifies endpoint responses and schema compliance.

### CKAN extension
The `ckanext-scheming/` directory includes `eosc-service-catalogue-schema-v3.yaml`, a CKAN scheming dataset profile that mirrors the EOSC v3 service bundle. Follow the instructions in `ckanext-scheming/README.md` to install `ckanext-scheming`, register the schema, and capture service metadata directly through the CKAN admin UI.

## Troubleshooting
- **`ModuleNotFoundError: jsonschema`** – ensure `pip install -r api/requirements.txt` has been executed inside your environment.
- **Schema validation failures** – check the offending bundle index in the error message; update the JSON fixture so it conforms to the relevant version under `api/schema/`.
- **Swagger missing schema details** – confirm `/api/v3/schema` (or `/api/v1/schema`) is reachable and the loader validation succeeded at startup.

## Contributing
Contributions are welcome. Fork the repository, create a feature branch, and submit a pull request. Please include updates to fixtures and tests when you extend the API.

## License
Distributed under the MIT License. See [`LICENSE`](LICENSE).

## Citation
If you reuse this demonstrator, cite it using [`CITATION.cff`](CITATION.cff).

## Support
Open an issue in this repository with detailed reproduction steps and logs. For general EOSC questions, contact the SURF Service Desk (`info@surf.nl`).

## Documentation
- Project overview: `README.md`
- Implementation reference: `api/app/main.py`, `api/app/data.py`
- Data fixtures and schema: `api/data/`
- SURF scraping utility: `scraper/`
- Test suite: `test/`
- CKAN scheming profile: `ckanext-scheming/`
- EOSC guideline source: [*EEN Federating Capabilities for EOSC Service Catalogues*](EEN Federating Capabilities for EOSC Service Catalogues_v1_10August2025.docx.md)
