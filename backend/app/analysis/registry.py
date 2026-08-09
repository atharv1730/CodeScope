"""Async clients for PyPI, the npm registry, and the OSV vulnerability API.

Each fetch is defensive: any network/parse failure returns a neutral result
(no latest version / no vulnerabilities) rather than failing the whole pass.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import httpx

PYPI_URL = "https://pypi.org/pypi/{name}/json"
NPM_URL = "https://registry.npmjs.org/{name}"
OSV_URL = "https://api.osv.dev/v1/query"

_TIMEOUT = httpx.Timeout(10.0)
_CONCURRENCY = 10

# Map our ecosystem tags to OSV's ecosystem identifiers.
_OSV_ECOSYSTEM = {"pypi": "PyPI", "npm": "npm"}


@dataclass
class RegistryResult:
    latest_version: str | None = None
    vulnerabilities: list[dict] = field(default_factory=list)


async def _fetch_latest(client: httpx.AsyncClient, ecosystem: str, name: str) -> str | None:
    try:
        if ecosystem == "pypi":
            r = await client.get(PYPI_URL.format(name=name))
            r.raise_for_status()
            return r.json().get("info", {}).get("version")
        if ecosystem == "npm":
            r = await client.get(NPM_URL.format(name=name))
            r.raise_for_status()
            return r.json().get("dist-tags", {}).get("latest")
    except (httpx.HTTPError, ValueError, KeyError):
        return None
    return None


async def _fetch_osv(
    client: httpx.AsyncClient, ecosystem: str, name: str, version: str | None
) -> list[dict]:
    osv_eco = _OSV_ECOSYSTEM.get(ecosystem)
    if not osv_eco or not version:
        return []
    payload = {"package": {"name": name, "ecosystem": osv_eco}, "version": version}
    try:
        r = await client.post(OSV_URL, json=payload)
        r.raise_for_status()
        vulns = r.json().get("vulns", []) or []
    except (httpx.HTTPError, ValueError):
        return []
    return [summarize_vuln(v) for v in vulns]


def summarize_vuln(v: dict) -> dict:
    """Compact one OSV vulnerability record down to the fields we surface."""
    return {
        "id": v.get("id"),
        "summary": v.get("summary")
        or (v.get("details", "")[:200] if v.get("details") else None),
        "severity": _extract_severity(v),
        "aliases": v.get("aliases", []),
    }


def _extract_severity(v: dict) -> str | None:
    sev = v.get("severity") or []
    if sev and isinstance(sev, list):
        return sev[0].get("score")
    # Some records nest severity under database_specific.
    ds = v.get("database_specific") or {}
    return ds.get("severity")


async def _fetch_one(
    client: httpx.AsyncClient, sem: asyncio.Semaphore, ecosystem: str, name: str, version: str | None
) -> RegistryResult:
    async with sem:
        latest, vulns = await asyncio.gather(
            _fetch_latest(client, ecosystem, name),
            _fetch_osv(client, ecosystem, name, version),
        )
    return RegistryResult(latest_version=latest, vulnerabilities=vulns)


async def fetch_all(
    items: list[tuple[str, str, str | None]]
) -> list[RegistryResult]:
    """items: list of (ecosystem, name, current_version). Returns aligned results."""
    sem = asyncio.Semaphore(_CONCURRENCY)
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": "CodeScope/0.1"}) as client:
        tasks = [_fetch_one(client, sem, eco, name, ver) for eco, name, ver in items]
        return await asyncio.gather(*tasks)
