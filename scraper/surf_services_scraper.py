"""Harvest service bundles from https://www.surf.nl/en/services.

Usage::

    python scraper/surf_services_scraper.py --output api/data/surf-services.json

The script replicates the manual curation process that generated the
``surf-services.json`` fixture bundled with the demonstrator. It scrapes every
service page, extracts key fields, and emits EOSC-compliant service bundles.

Dependencies:
    - requests
    - beautifulsoup4

Install them with ``pip install requests beautifulsoup4`` before running the
script.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.surf.nl"
LIST_URL = f"{BASE_URL}/en/services"
CONTACT_PAGE = f"{BASE_URL}/en/about/contact-with-surf"
TERMS_URL = f"{BASE_URL}/en/terms-and-conditions"
PRIVACY_URL = f"{BASE_URL}/en/privacy-statement"
TRAINING_URL = f"{BASE_URL}/en/training"
SCIENTIFIC_SUBDOMAIN = (
    "scientific_subdomain-engineering_and_technology-"
    "electrical_electronic_and_information_engineering"
)

# Controlled vocabulary mappings keyed by the category segment in the service URL.
CATEGORY_MAP: Mapping[str, Dict[str, object]] = {
    "compute": {
        "category": "category-access_physical_and_eInfrastructures-compute",
        "subcategory": "subcategory-access_physical_and_eInfrastructures-compute-workload_management",
        "marketplace": "marketplace_location-access_computing_and_storage_resources",
        "service_category": "service_category-compute",
        "horizontal": False,
    },
    "storage-data-management": {
        "category": "category-access_physical_and_eInfrastructures-data_storage",
        "subcategory": "subcategory-access_physical_and_eInfrastructures-data_storage-backup",
        "marketplace": "marketplace_location-access_computing_and_storage_resources",
        "service_category": "service_category-storage",
        "horizontal": False,
    },
    "identity-access-management": {
        "category": "category-security_and_operations-security_and_identity",
        "subcategory": "subcategory-security_and_operations-security_and_identity-user_authentication",
        "marketplace": "marketplace_location-find_supporting_services_for_eInfras",
        "service_category": "service_category-other",
        "horizontal": True,
    },
    "identity-and-access-management": {
        "category": "category-security_and_operations-security_and_identity",
        "subcategory": "subcategory-security_and_operations-security_and_identity-user_authentication",
        "marketplace": "marketplace_location-find_supporting_services_for_eInfras",
        "service_category": "service_category-other",
        "horizontal": True,
    },
    "network-connectivity": {
        "category": "category-access_physical_and_eInfrastructures-network",
        "subcategory": "subcategory-access_physical_and_eInfrastructures-network-virtual_nework",
        "marketplace": "marketplace_location-access_computing_and_storage_resources",
        "service_category": "service_category-other",
        "horizontal": True,
    },
    "security": {
        "category": "category-security_and_operations-security_and_identity",
        "subcategory": "subcategory-security_and_operations-security_and_identity-threat_protection",
        "marketplace": "marketplace_location-find_supporting_services_for_eInfras",
        "service_category": "service_category-other",
        "horizontal": True,
    },
    "publishing": {
        "category": "category-sharing_and_discovery-data",
        "subcategory": "subcategory-sharing_and_discovery-data-statistical_data",
        "marketplace": "marketplace_location-publish_research_outputs",
        "service_category": "service_category-data_source",
        "horizontal": False,
    },
    "procurement-delivery": {
        "category": "category-security_and_operations-operations_and_infrastructure_management_services",
        "subcategory": "subcategory-security_and_operations-operations_and_infrastructure_management_services-accounting",
        "marketplace": "marketplace_location-find_supporting_services_for_eInfras",
        "service_category": "service_category-other",
        "horizontal": True,
    },
    "procurement-contracting": {
        "category": "category-security_and_operations-operations_and_infrastructure_management_services",
        "subcategory": "subcategory-security_and_operations-operations_and_infrastructure_management_services-accounting",
        "marketplace": "marketplace_location-find_supporting_services_for_eInfras",
        "service_category": "service_category-other",
        "horizontal": True,
    },
    "flexible-education": {
        "category": "category-sharing_and_discovery-applications",
        "subcategory": "subcategory-sharing_and_discovery-applications-applications_repository",
        "marketplace": "marketplace_location-access_training_material",
        "service_category": "service_category-other",
        "horizontal": False,
    },
}

# Manual overrides applied after scraping to better reflect positioning observed
# on the SURF website.
BUNDLE_OVERRIDES: Mapping[str, Dict[str, object]] = {
    "surf/surf-research-cloud": {
        "service": {
            "targetUsers": [
                "target_user-providers",
                "target_user-research_communities",
                "target_user-research_infrastructure_managers",
                "target_user-research_projects",
                "target_user-researchers",
            ],
            "marketplaceLocations": [
                "marketplace_location-access_computing_and_storage_resources",
                "marketplace_location-build_analysis_environment",
            ],
        }
    },
    "surf/surfdrive": {
        "service": {
            "targetUsers": [
                "target_user-research_communities",
                "target_user-research_groups",
                "target_user-research_projects",
                "target_user-researchers",
                "target_user-students",
            ],
            "marketplaceLocations": ["marketplace_location-manage_research_data"],
            "accessModes": ["access_mode-free_conditionally"],
            "order": "https://surfdrive.surf.nl",
            "accessPolicy": "https://surfdrive.surf.nl",
        }
    },
    "surf/surfsecureid": {
        "service": {
            "targetUsers": [
                "target_user-providers",
                "target_user-research_communities",
                "target_user-research_infrastructure_managers",
                "target_user-research_projects",
                "target_user-researchers",
            ],
            "horizontalService": True,
        }
    },
    "surf/surffilesender": {
        "service": {
            "marketplaceLocations": ["marketplace_location-manage_research_data"],
            "accessModes": ["access_mode-free"],
        }
    },
    "surf/edusources": {
        "service": {
            "targetUsers": [
                "target_user-publishers",
                "target_user-research_communities",
                "target_user-research_projects",
                "target_user-researchers",
                "target_user-students",
            ],
            "marketplaceLocations": ["marketplace_location-publish_research_outputs"],
        }
    },
    "surf/kies-op-maat": {
        "service": {
            "targetUsers": [
                "target_user-researchers",
                "target_user-research_projects",
                "target_user-students",
            ],
            "marketplaceLocations": ["marketplace_location-access_training_material"],
        }
    },
}

DEFAULT_CONTACT = {
    "first_name": "SURF",
    "last_name": "Service Desk",
    "email": "info@surf.nl",
    "phone": "+31 88 787 30 00",
}


def discover_service_pages(session: requests.Session) -> List[str]:
    """Return absolute URLs for all service detail pages."""
    response = session.get(LIST_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links = {
        urljoin(BASE_URL, link["href"])
        for link in soup.select('a[href^="/en/services/"]')
        if link.get("href")
    }
    # Filter out listing pages; detail pages have at least one extra segment.
    service_links = sorted({url for url in links if url.count("/") > LIST_URL.count("/")})
    return service_links


def _slug_from_url(url: str) -> str:
    return "/".join(p for p in urlparse(url).path.split("/") if p)[-1]


def _category_slug(url: str) -> str:
    parts = [p for p in urlparse(url).path.split("/") if p]
    return parts[2] if len(parts) > 2 else "security"


def _make_abbreviation(slug: str) -> str:
    tokens = [token for token in re.split(r"[-_/]", slug) if token]
    return ("".join(token[0] for token in tokens)).upper()[:6] or slug[:6].upper()


@dataclass
class Contact:
    first_name: str
    last_name: str
    email: str
    phone: str

    @classmethod
    def from_block(cls, block: BeautifulSoup) -> "Contact":
        name_node = block.select_one("h2")
        first_name, last_name = DEFAULT_CONTACT["first_name"], DEFAULT_CONTACT["last_name"]
        if name_node:
            name_parts = name_node.get_text(strip=True).split(maxsplit=1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else DEFAULT_CONTACT["last_name"]
        email_node = block.select_one('a[href^="mailto:"]')
        email = email_node["href"].split(":", 1)[1] if email_node else DEFAULT_CONTACT["email"]
        phone_node = block.select_one('a[href^="tel:"]')
        phone = phone_node.get_text(strip=True) if phone_node else DEFAULT_CONTACT["phone"]
        return cls(first_name, last_name, email, phone)


def scrape_service(url: str, session: requests.Session) -> Dict[str, object]:
    """Scrape a single SURF service detail page into a bundle."""
    response = session.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title_node = soup.find("h1")
    if not title_node:
        raise RuntimeError(f"Missing title for {url}")
    title = title_node.get_text(strip=True)

    meta_desc = soup.find("meta", attrs={"name": "description"})
    description = unescape(meta_desc["content"]).strip() if meta_desc else title

    benefit_title = soup.select_one(
        ".paragraph--type--benefit .field--name-field-title, .paragraph--type--benefit h3"
    )
    tagline = benefit_title.get_text(strip=True) if benefit_title else description.split(".")[0]

    action_link = soup.select_one(".paragraph--type--action a")
    order_url = action_link.get("href") if action_link else CONTACT_PAGE
    if order_url.startswith("/"):
        order_url = urljoin(BASE_URL, order_url)

    contact_block = soup.select_one(".paragraph--type--contact")
    contact = Contact.from_block(contact_block) if contact_block else Contact(**DEFAULT_CONTACT)

    category_slug = _category_slug(url)
    service_slug = _slug_from_url(url)
    mapping = CATEGORY_MAP.get(category_slug, CATEGORY_MAP["security"])

    slug_tokens = [token for token in re.split(r"[-_/]", service_slug) if token]
    tags = sorted(set(token.lower() for token in slug_tokens + [category_slug, "surf"]))

    timestamp = str(int(time.time() * 1000))

    bundle: MutableMapping[str, object] = {
        "metadata": {
            "registeredBy": "surf-scraper",
            "registeredAt": timestamp,
            "modifiedBy": "surf-scraper",
            "modifiedAt": timestamp,
            "published": True,
        },
        "active": True,
        "suspended": False,
        "draft": False,
        "legacy": False,
        "status": "approved",
        "resourceOrganisationGroupID": "surf-services",
        "nodeId": "surf-node",
        "sites": [
            {
                "name": title,
                "endpoints": [
                    {
                        "name": "Service portal",
                        "type": "endpoint_type-gui",
                        "url": url,
                        "monitoringServiceType": "eu.eosc.container_platform.gui",
                    }
                ],
            }
        ],
        "service": {
            "id": f"surf/{service_slug}",
            "abbreviation": _make_abbreviation(service_slug),
            "name": title,
            "resourceOrganisation": "SURF",
            "resourceProviders": ["SURF"],
            "webpage": url,
            "alternativeIdentifiers": [{"type": "slug", "value": service_slug}],
            "description": description,
            "tagline": tagline,
            "logo": "https://www.surf.nl/themes/surf/favicons/apple-touch-icon.png",
            "scientificDomains": [
                {
                    "scientificDomain": "scientific_domain-engineering_and_technology",
                    "scientificSubdomain": SCIENTIFIC_SUBDOMAIN,
                }
            ],
            "categories": [
                {
                    "category": mapping["category"],
                    "subcategory": mapping["subcategory"],
                }
            ],
            "targetUsers": [
                "target_user-research_communities",
                "target_user-research_projects",
                "target_user-researchers",
            ],
            "accessTypes": ["access_type-remote"],
            "accessModes": ["access_mode-other"],
            "tags": tags,
            "horizontalService": mapping["horizontal"],
            "serviceCategories": [mapping["service_category"]],
            "marketplaceLocations": [mapping["marketplace"]],
            "geographicalAvailabilities": ["EU"],
            "languageAvailabilities": ["en"],
            "resourceGeographicLocations": ["NL"],
            "mainContact": {
                "firstName": contact.first_name,
                "lastName": contact.last_name,
                "email": contact.email,
                "phone": contact.phone,
                "position": "Contact person",
                "organisation": "SURF",
            },
            "publicContacts": [
                {
                    "firstName": contact.first_name,
                    "lastName": contact.last_name,
                    "email": contact.email,
                    "phone": contact.phone,
                    "organisation": "SURF",
                }
            ],
            "helpdeskEmail": contact.email,
            "securityContactEmail": "info@surf.nl",
            "trl": "trl-9",
            "lifeCycleStatus": "life_cycle_status-operation",
            "helpdeskPage": CONTACT_PAGE,
            "userManual": url,
            "termsOfUse": TERMS_URL,
            "privacyPolicy": PRIVACY_URL,
            "accessPolicy": order_url,
            "orderType": "order_type-order_required",
            "order": order_url,
            "paymentModel": CONTACT_PAGE,
            "pricing": CONTACT_PAGE,
            "trainingInformation": TRAINING_URL,
            "statusMonitoring": LIST_URL,
            "maintenance": LIST_URL,
        },
    }

    apply_overrides(bundle)
    return bundle  # type: ignore[return-value]


def apply_overrides(bundle: MutableMapping[str, object]) -> None:
    """Patch scraped bundles with any manual overrides."""
    service = bundle["service"]  # type: ignore[index]
    overrides = BUNDLE_OVERRIDES.get(service["id"])
    if not overrides:
        return
    for key, value in overrides.get("service", {}).items():
        service[key] = value


def scrape_all(limit: int | None = None, delay: float = 0.0) -> List[Dict[str, object]]:
    """Scrape every service page and return the resulting bundles."""
    session = requests.Session()
    bundles: List[Dict[str, object]] = []
    for index, url in enumerate(discover_service_pages(session), start=1):
        if limit is not None and index > limit:
            break
        bundles.append(scrape_service(url, session))
        if delay:
            time.sleep(delay)
    return bundles


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape SURF services into EOSC bundles")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("api/data/surf-services.json"),
        help="Where to write the generated JSON (default: api/data/surf-services.json)",
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bundles = scrape_all(limit=args.limit, delay=args.delay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundles, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(bundles)} bundles to {args.output}")


if __name__ == "__main__":
    main()
