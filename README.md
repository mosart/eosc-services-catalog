# EOSC Service Catalogue Demonstrator API

## TL;DR
- FastAPI demo that serves EOSC-compliant service bundles from JSON fixtures.
- Swagger UI available at `/api/v1/docs` (root URL redirects there automatically).
- Includes SURF catalogue sample data, scraper, and pytest suite with schema validation.

## Purpose
Provide a minimal, self-contained example of the API described in Appendix A of *EEN Federating Capabilities for EOSC Service Catalogues*. The project helps EOSC Nodes prototype a compliant service catalogue endpoint without standing up a full backend.

## Features
- FastAPI implementation with versioned endpoints, pagination, filtering, and sorting.
- OpenAPI document enriched with the official EOSC service-bundle JSON schema.
- Fixture loader that validates data against `api/data/eosc_service_catalogue.schema.json`.
- SURF catalogue dataset generator and scraped reference bundle.
- Pytest smoke tests that validate API responses against the schema.

## Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
```

## Configuration
- Data fixtures live in `api/data/`. Replace or extend `services.json` / `surf-services.json` with your own bundles, or add new filenames to `_DATA_FILES` in `api/app/data.py`; the loader will continue to validate them.
- Optional scraper dependencies are listed in `scraper/requirements.txt`.
- Adjust `_ALLOWED_SORT_FIELDS` or extend the FastAPI routes in `api/app/main.py` to support additional behaviour.

## Usage
### API
Run the development server:
```bash
uvicorn api.app.main:app --reload
```
Browse to `http://127.0.0.1:8000/` to reach the Swagger UI. Key endpoints and sample calls:
- `GET /healthz` – health check
  ```bash
  curl http://127.0.0.1:8000/healthz
  ```
- `GET /api/v1/services` – query catalogue entries
  ```bash
  curl 'http://127.0.0.1:8000/api/v1/services?keyword=cloud&quantity=5'
  ```
  ```python
  import requests

  resp = requests.get(
      'http://127.0.0.1:8000/api/v1/services',
      params={'keyword': 'cloud', 'quantity': 5},
      timeout=10,
  )
  resp.raise_for_status()
  print(resp.json()['items'][0]['service']['name'])
  ```
- `GET /api/v1/services/{prefix}/{suffix}` – fetch a specific bundle
  ```bash
  curl http://127.0.0.1:8000/api/v1/services/surf/surf-research-cloud
  ```
- `GET /api/v1/schema` – retrieve the EOSC schema
  ```bash
  curl http://127.0.0.1:8000/api/v1/schema | jq '.title'
  ```
- `GET /api/v1/openapi.json` – download the OpenAPI document
  ```bash
  curl http://127.0.0.1:8000/api/v1/openapi.json
  ```

For a production-style run:
```bash
uvicorn api.app.main:app --host 0.0.0.0 --port 8000
```

### Scraper
Harvest the SURF catalogue or regenerate `surf-services.json`:
```bash
pip install -r scraper/requirements.txt
python scraper/surf_services_scraper.py --output api/data/surf-services.json
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

## Troubleshooting
- **`ModuleNotFoundError: jsonschema`** – ensure `pip install -r api/requirements.txt` has been executed inside your environment.
- **Schema validation failures** – check the offending bundle index in the error message; update the JSON fixture to match `api/data/eosc_service_catalogue.schema.json`.
- **Swagger missing schema details** – confirm `/api/v1/schema` is reachable and the loader validation succeeded at startup.

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
- EOSC guideline source: [*EEN Federating Capabilities for EOSC Service Catalogues*](EEN Federating Capabilities for EOSC Service Catalogues_v1_10August2025.docx.md)
