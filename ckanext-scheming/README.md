# EOSC Service Catalogue v3 CKAN Schema

This directory contains a CKAN [ckanext-scheming](https://github.com/ckan/ckanext-scheming/) dataset schema that mirrors the
[EOSC Service Bundle v3 JSON Schema](../specs/eosc_service_catalogue.schema_v3.json).
It enables CKAN publishers to create and edit service metadata directly from the
CKAN admin UI while staying aligned with the EOSC federation profile.

## Included files

| File | Purpose |
| --- | --- |
| `eosc-service-catalogue-schema-v3.yaml` | CKAN scheming definition for the `service` dataset type. |
| `README.md` | Usage instructions (this document). |

## Installing `ckanext-scheming`

1. Activate your CKAN virtual environment and install the extension:

   ```bash
   cd $CKAN_VENV/src
   pip install -e "git+https://github.com/ckan/ckanext-scheming.git#egg=ckanext-scheming"
   ```

2. Enable the scheming plugins in `ckan.ini` (append to the existing `ckan.plugins` line):

   ```ini
   ckan.plugins = scheming_datasets scheming_groups scheming_organizations ...
   ```

3. Point CKAN at the presets file (optional if you stay with the defaults):

   ```ini
   scheming.presets = ckanext.scheming:presets.json
   ```

## Enabling the EOSC service schema

1. Copy `eosc-service-catalogue-schema-v3.yaml` into a location that is importable by CKAN.
   You can keep it inside this directory and reference it using a filesystem path, e.g.:

   ```ini
   scheming.dataset_schemas = /etc/ckan/default/eosc-service-catalogue-schema-v3.yaml
   ```

   or, when packaging it in a CKAN plugin module:

   ```ini
   scheming.dataset_schemas = ckanext.eosc_service:ckanext-scheming/eosc-service-catalogue-schema-v3.yaml
   ```

2. Restart CKAN (web server and background jobs) so the new configuration is loaded.

3. After restarting, datasets created with `dataset_type=service` will use the new form and
   validation rules supplied by the schema file.

## Schema overview

The YAML schema maps each field from the EOSC Service Bundle model onto CKAN form elements:

- **Service identity** – `bundle_id`, `title`, `name`, and `abbreviation` capture the primary
  identifiers exposed in the federation API.
- **Core description** – `notes`, `tagline`, `webpage`, and `logo` align with the mandatory
  descriptive fields from Appendix B.
- **Scientific coverage** – the `scientific_classification` repeating subfields let publishers
  add one or more domain/subdomain pairs. This mirrors the nested array used in the JSON schema.
- **Service categories** – a second repeating subfield pair (`category` and `subcategory`) keeps
  the relationship between top-level categories and their controlled subcategories.
- **Target users & availability** – checkbox and multi-text widgets model the controlled
  vocabularies for `targetUsers`, `trl`, `orderType`, `access_mode`, and language codes.
- **Compliance URLs** – dedicated fields (`user_manual`, `terms_of_use`, `privacy_policy`,
  `access_policy`) ensure that important service policy links are recorded with URL validation.
- **Support contacts** – optional helpdesk and security emails mirror the EOSC profile.
- **Tagging** – the CKAN tag widget (`tag_string_autocomplete`) is retained for free-text keywords
  that complement the controlled vocabulary fields.

The schema relies exclusively on dataset-level fields; resource-level fields are intentionally
omitted because EOSC service bundles model a single logical resource rather than downloadable
files.

## Working with the schema

1. Navigate to **Datasets → Add Dataset** and choose the `service` dataset type.
2. Complete the form. Required fields match the EOSC v3 mandatory list (e.g. bundle ID, service
   name, description, scientific classification, TRL, order type, and at least one target user).
3. Use the repeating sections to add multiple scientific domain/subdomain pairs or category/
   subcategory combinations. Click **Add another** within each block to append additional entries.
4. Save the dataset. CKAN will apply the scheming validators, guaranteeing that all controlled
   vocabulary values come from the EOSC vocabularies.
5. The dataset can now be exported or transformed back into the EOSC JSON representation when
   synchronising with the federation API.

## Mapping notes

- The schema reuses the EOSC vocabulary JSON files to populate dropdown choices, so the options
  stay aligned with the upstream specification.
- Some EOSC arrays (e.g. `scientificDomains`, `categories`) are handled with `repeating_subfields`
  to preserve the nested pairing between parent and child values.
- Free-text arrays such as `languageAvailabilities` and `alternativeIdentifiers` use the
  `multiple_text` preset, prompting editors to add as many entries as needed.
- Additional EOSC fields (`tags`, `accessTypes`) are represented by standard CKAN widgets so the
  resulting datasets remain compatible with the rest of the CKAN UI.

## Next steps

- Extend the schema with CKAN presets or custom snippets if you want friendlier widgets
  (auto-complete, dependent dropdowns) for the larger vocabularies.
- Create API transforms that serialise CKAN `service` datasets back into the
  `eosc_service_catalogue.schema_v3.json` structure for harvesting.
- Add automated tests using CKAN’s `scheming test` helpers to guard against regressions when
  the EOSC vocabularies evolve.
