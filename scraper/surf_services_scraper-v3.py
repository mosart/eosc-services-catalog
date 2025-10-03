"""Harvest SURF services into EOSC service bundle objects conforming to the v3 schema.

Example::

    python scraper/surf_services_scraper-v3.py \
        --output api/data/v3/surf-services-all-v3.json
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Sequence
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from jsonschema import Draft202012Validator

BASE_URL = "https://www.surf.nl"
LIST_URL = f"{BASE_URL}/en/services"
CONTACT_PAGE = f"{BASE_URL}/en/about/contact-with-surf"
TERMS_URL = f"{BASE_URL}/en/terms-and-conditions"
PRIVACY_URL = f"{BASE_URL}/en/privacy-statement"

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "specs" / "eosc_service_catalogue.schema_v3.json"
DEFAULT_OUTPUT = ROOT_DIR / "api" / "app" / "data" / "v3" / "surf-services-all-v3.json"

SCIENTIFIC_DOMAIN = "scientific_domain-engineering_and_technology"
SCIENTIFIC_SUBDOMAIN = (
    "scientific_subdomain-engineering_and_technology-"
    "electrical_electronic_and_information_engineering"
)
DEFAULT_TARGET_USERS = [
    "target_user-research_communities",
    "target_user-research_groups",
    "target_user-research_projects",
    "target_user-researchers",
]
DEFAULT_TRL = "trl-8"
DEFAULT_ACCESS_TYPE = "access_mode-other"
DEFAULT_ORDER_TYPE = "order_type-order_required"
LOGO_URL = "https://www.surf.nl/themes/surf/logo.svg"

CATEGORY_MAP: Mapping[str, Dict[str, str]] = {
    "compute": {
        "category": "category-access_physical_and_eInfrastructures-compute",
        "subcategory": "subcategory-access_physical_and_eInfrastructures-compute-workload_management",
    },
    "storage-data-management": {
        "category": "category-access_physical_and_eInfrastructures-data_storage",
        "subcategory": "subcategory-access_physical_and_eInfrastructures-data_storage-backup",
    },
    "identity-access-management": {
        "category": "category-security_and_operations-security_and_identity",
        "subcategory": "subcategory-security_and_operations-security_and_identity-user_authentication",
    },
    "identity-and-access-management": {
        "category": "category-security_and_operations-security_and_identity",
        "subcategory": "subcategory-security_and_operations-security_and_identity-user_authentication",
    },
    "network-connectivity": {
        "category": "category-access_physical_and_eInfrastructures-network",
        "subcategory": "subcategory-access_physical_and_eInfrastructures-network-virtual_nework",
    },
    "security": {
        "category": "category-security_and_operations-security_and_identity",
        "subcategory": "subcategory-security_and_operations-security_and_identity-threat_protection",
    },
    "publishing": {
        "category": "category-sharing_and_discovery-data",
        "subcategory": "subcategory-sharing_and_discovery-data-statistical_data",
    },
    "procurement-delivery": {
        "category": "category-security_and_operations-operations_and_infrastructure_management_services",
        "subcategory": "subcategory-security_and_operations-operations_and_infrastructure_management_services-accounting",
    },
    "procurement-contracting": {
        "category": "category-security_and_operations-operations_and_infrastructure_management_services",
        "subcategory": "subcategory-security_and_operations-operations_and_infrastructure_management_services-accounting",
    },
    "flexible-education": {
        "category": "category-sharing_and_discovery-applications",
        "subcategory": "subcategory-sharing_and_discovery-applications-applications_repository",
    },
}

BUNDLE_OVERRIDES: Mapping[str, Dict[str, object]] = {
    "surf-research-cloud": {
        "targetUsers": [
            "target_user-providers",
            "target_user-research_communities",
            "target_user-research_infrastructure_managers",
            "target_user-research_projects",
            "target_user-researchers",
        ],
        "accessMode": "access_mode-other",
        "languageAvailabilities": ["EN", "NL"],
    },
    "surfdrive": {
        "targetUsers": [
            "target_user-research_communities",
            "target_user-research_groups",
            "target_user-research_projects",
            "target_user-researchers",
            "target_user-students",
        ],
        "accessMode": "access_mode-free_conditionally",
        "orderType": "order_type-open_access",
    },
    "surfsecureid": {
        "targetUsers": [
            "target_user-providers",
            "target_user-research_communities",
            "target_user-research_infrastructure_managers",
            "target_user-research_projects",
            "target_user-researchers",
        ],
    },
    "surffilesender": {
        "accessMode": "access_mode-free",
        "orderType": "order_type-open_access",
    },
    "edusources": {
        "targetUsers": [
            "target_user-publishers",
            "target_user-research_communities",
            "target_user-research_projects",
            "target_user-researchers",
            "target_user-students",
        ],
        "accessMode": "access_mode-other",
    },
    "kies-op-maat": {
        "targetUsers": [
            "target_user-researchers",
            "target_user-research_projects",
            "target_user-students",
        ],
        "languageAvailabilities": ["NL"],
    },
}


@dataclass
class Contact:
    first_name: str
    last_name: str
    email: str
    phone: str

    @classmethod
    def from_block(cls, block: BeautifulSoup) -> "Contact":
        first_name = "SURF"
        last_name = "Service Desk"
        email = "info@surf.nl"
        phone = "+31 88 787 30 00"
        if block:
            name_node = block.select_one("h2")
            if name_node:
                parts = name_node.get_text(strip=True).split(maxsplit=1)
                first_name = parts[0]
                if len(parts) > 1:
                    last_name = parts[1]
            email_node = block.select_one('a[href^="mailto:"]')
            if email_node and email_node.get("href"):
                email = email_node["href"].split(":", 1)[1]
            phone_node = block.select_one('a[href^="tel:"]')
            if phone_node:
                phone = phone_node.get_text(strip=True)
        return cls(first_name, last_name, email, phone)


def discover_service_pages(session: requests.Session) -> List[str]:
    response = session.get(LIST_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links = {
        urljoin(BASE_URL, link["href"])
        for link in soup.select('a[href^="/en/services/"]')
        if link.get("href")
    }
    service_links = []
    for url in links:
        parts = [segment for segment in urlparse(url).path.split("/") if segment]
        if len(parts) >= 4:  # /en/services/<category>/<service>
            service_links.append(url)
    service_links.sort()
    print(f"Discovered {len(service_links)} service detail pages")
    return service_links


def _slug_from_url(url: str) -> str:
    parts = [segment for segment in urlparse(url).path.split("/") if segment]
    return parts[-1]


def _category_slug(url: str) -> str:
    parts = [segment for segment in urlparse(url).path.split("/") if segment]
    return parts[2] if len(parts) > 2 else "security"


def _make_abbreviation(slug: str) -> str:
    tokens = [token for token in re.split(r"[-_/]", slug) if token]
    return ("".join(token[0] for token in tokens)).upper()[:6] or slug[:6].upper()


def _unique(values: Sequence[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def scrape_service(url: str, session: requests.Session) -> Dict[str, object]:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title_node = soup.find("h1")
    if not title_node:
        raise RuntimeError(f"Missing title for {url}")
    title = title_node.get_text(strip=True)

    meta_desc = soup.find("meta", attrs={"name": "description"})
    description = unescape(meta_desc["content"]).strip() if meta_desc else title

    tagline_node = soup.select_one(
        ".paragraph--type--benefit .field--name-field-title, .paragraph--type--benefit h3"
    )
    tagline = tagline_node.get_text(strip=True) if tagline_node else description.split(".")[0]

    action_link = soup.select_one(".paragraph--type--action a")
    order_url = action_link.get("href") if action_link else CONTACT_PAGE
    if order_url.startswith("/"):
        order_url = urljoin(BASE_URL, order_url)

    contact_block = soup.select_one(".paragraph--type--contact")
    contact = Contact.from_block(contact_block)

    category_slug = _category_slug(url)
    service_slug = _slug_from_url(url)
    mapping = CATEGORY_MAP.get(category_slug, CATEGORY_MAP["security"])

    slug_tokens = [token for token in re.split(r"[-_/]", service_slug) if token]
    tags = sorted(set(token.lower() for token in slug_tokens + [category_slug, "surf"]))

    bundle_id = f"surf-node:servicebundle:{service_slug}"

    service: MutableMapping[str, object] = {
        "id": bundle_id,
        "abbreviation": _make_abbreviation(service_slug),
        "name": title,
        "webpage": url,
        "description": description,
        "tagline": tagline,
        "logo": LOGO_URL,
        "scientificDomains": [
            {
                "scientificDomain": SCIENTIFIC_DOMAIN,
                "scientificSubdomain": SCIENTIFIC_SUBDOMAIN,
            }
        ],
        "categories": [
            {
                "category": mapping["category"],
                "subcategory": mapping["subcategory"],
            }
        ],
        "targetUsers": DEFAULT_TARGET_USERS[:],
        "accessMode": DEFAULT_ACCESS_TYPE,
        "tags": tags,
        "languageAvailabilities": ["EN", "NL"],
        "helpdeskEmail": contact.email.strip(),
        "securityContactEmail": "info@surf.nl",
        "trl": DEFAULT_TRL,
        "userManual": url,
        "termsOfUse": TERMS_URL,
        "privacyPolicy": PRIVACY_URL,
        "accessPolicy": order_url,
        "orderType": DEFAULT_ORDER_TYPE,
    }

    overrides = BUNDLE_OVERRIDES.get(service_slug)
    if overrides:
        for key, value in overrides.items():
            service[key] = value

    service["targetUsers"] = _unique([
        entry.strip() for entry in service.get("targetUsers", []) if entry
    ])
    service["languageAvailabilities"] = _unique(
        [code.upper() for code in service.get("languageAvailabilities", ["EN"])]
    )
    service["tags"] = _unique([tag.strip() for tag in service.get("tags", []) if tag])

    bundle: Dict[str, object] = {
        "id": bundle_id,
        "service": service,
    }

    return bundle


def scrape_all(limit: int | None = None, delay: float = 0.0) -> List[Dict[str, object]]:
    session = requests.Session()
    bundles: List[Dict[str, object]] = []
    for index, url in enumerate(discover_service_pages(session), start=1):
        if limit is not None and index > limit:
            break
        print(f"[{index}] Fetching {url}")
        bundles.append(scrape_service(url, session))
        if delay:
            time.sleep(delay)
    return bundles


def load_validator(schema_path: Path) -> Draft202012Validator:
    with schema_path.open(encoding="utf-8") as fp:
        schema = json.load(fp)
    return Draft202012Validator(schema)


def validate_bundles(bundles: Iterable[Dict[str, object]], validator: Draft202012Validator) -> None:
    errors = []
    total = 0
    for bundle in bundles:
        total += 1
        for error in validator.iter_errors(bundle):
            location = ".".join(str(part) for part in error.path)
            errors.append(f"{bundle.get('id', '<unknown>')} -> {location}: {error.message}")
    if errors:
        raise ValueError("\n".join(errors))
    print(f"Validation succeeded for {total} bundles")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape SURF services into EOSC v3 bundles")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to write the JSON (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Scrape only the first N services (for debugging)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Optional delay between requests in seconds",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=SCHEMA_PATH,
        help="Path to the JSON schema used for validation",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validator = load_validator(args.schema)
    bundles = scrape_all(limit=args.limit, delay=args.delay)
    validate_bundles(bundles, validator)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundles, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(bundles)} bundles to {args.output}")


if __name__ == "__main__":
    main()
