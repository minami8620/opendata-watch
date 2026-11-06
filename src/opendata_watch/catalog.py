"""Fetch datasets from a CKAN catalog and reduce them to small, comparable snapshots."""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

DEFAULT_API = "https://catalog.data.metro.tokyo.lg.jp/api/3/action"
USER_AGENT = "opendata-watch/0.1 (+https://github.com/minami8620/opendata-watch)"


@dataclass(frozen=True)
class Resource:
    id: str
    name: str
    url: str
    format: str
    last_modified: str


@dataclass(frozen=True)
class Dataset:
    id: str
    title: str
    organization: str
    modified: str
    page_url: str
    resources: tuple[Resource, ...]


@dataclass(frozen=True)
class Watch:
    """One saved search: a CKAN query plus an optional organization filter."""

    name: str
    query: str
    organization: str | None = None
    rows: int = 50


def to_dataset(package: dict, site: str) -> Dataset:
    resources = tuple(
        Resource(
            id=r["id"],
            name=(r.get("name") or "").strip(),
            url=r.get("url") or "",
            format=(r.get("format") or "").upper(),
            last_modified=r.get("last_modified") or r.get("created") or "",
        )
        for r in package.get("resources", [])
    )
    org = (package.get("organization") or {}).get("title", "")
    return Dataset(
        id=package["name"],
        title=package["title"].strip(),
        organization=org,
        modified=package["metadata_modified"],
        page_url=f"{site}/dataset/{package['name']}",
        resources=resources,
    )


def site_root(api: str) -> str:
    return api.split("/api/")[0]


def search(
    session: requests.Session, watch: Watch, api: str = DEFAULT_API, retries: int = 1
) -> list[Dataset]:
    """Return the most recently modified datasets matching ``watch`` (one request per watch)."""
    params = {"q": watch.query, "rows": watch.rows, "sort": "metadata_modified desc"}
    if watch.organization:
        params["fq"] = f'organization:"{watch.organization}"'
    for attempt in range(retries + 1):
        try:
            response = session.get(f"{api}/package_search", params=params, timeout=30)
            response.raise_for_status()
            break
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(5)
    results = response.json()["result"]["results"]
    return [to_dataset(p, site_root(api)) for p in results]


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session
