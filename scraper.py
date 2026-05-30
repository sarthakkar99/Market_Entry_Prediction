"""
scraper.py
----------
Fetch SERP results via Bright Data REST API.
Job agent uses LinkedIn-targeted queries.
Falls back to mock data when API key is missing or call fails.
"""

import httpx
import random
from urllib.parse import quote_plus

from config import (
    BRIGHTDATA_API_KEY,
    BRIGHTDATA_API_URL,
    BRIGHTDATA_ZONE,
    MOCK_MODE,
    SERP_RESULTS,
    AGENT_TIMEOUT,
)


# ── Public API ────────────────────────────────────────────────────────────────

async def fetch_serp(query: str, agent_id: str = "") -> list[dict]:
    if MOCK_MODE:
        return _mock_results(query, agent_id)
    try:
        return await _brightdata_serp(query)
    except Exception as exc:
        print(f"[scraper] Bright Data error ({exc}), falling back to mock")
        return _mock_results(query, agent_id)


# ── Bright Data REST API ──────────────────────────────────────────────────────

async def _brightdata_serp(query: str) -> list[dict]:
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {BRIGHTDATA_API_KEY}",
    }
    payload = {
        "zone":   BRIGHTDATA_ZONE,
        "url":    f"https://www.google.com/search?q={quote_plus(query)}&num={SERP_RESULTS}&brd_json=1",
        "format": "raw",
    }
    async with httpx.AsyncClient(timeout=AGENT_TIMEOUT) as client:
        resp = await client.post(BRIGHTDATA_API_URL, headers=headers, json=payload)
        resp.raise_for_status()

    return _parse_json_results(resp.json())


def _parse_json_results(data: dict) -> list[dict]:
    results = []
    for item in data.get("organic", [])[:SERP_RESULTS]:
        results.append({
            "title":   item.get("title", ""),
            "url":     item.get("link", ""),
            "snippet": item.get("description", ""),
        })
    return results


# ── Mock data ─────────────────────────────────────────────────────────────────

_MOCK_POOL = {
    "job_posts": [
        ("{company} | Head of {market} Products | {country} — LinkedIn",
         "https://linkedin.com/jobs/view/100001",
         "{company} seeks Head of {market} Products in {country}. 7+ yrs {market} experience required."),
        ("{company} | Senior {market} Compliance Manager | {country} — LinkedIn",
         "https://linkedin.com/jobs/view/100002",
         "Build {company}'s {market} compliance function from scratch in {country}. Reports to VP New Verticals."),
        ("{company} | {market} Business Development Lead | {country} — LinkedIn",
         "https://linkedin.com/jobs/view/100003",
         "Drive {company}'s {market} go-to-market in {country}. Prior {market} startup experience preferred."),
        ("{company} | {market} Partnerships Manager | {country} — LinkedIn",
         "https://linkedin.com/jobs/view/100004",
         "Own {company}'s strategic {market} partnerships across {country}. Must have existing {market} network."),
    ],
    "domain_regs": [
        ("{company_lower}{market_lower}.com — WHOIS",
         "https://whois.domaintools.com/{company_lower}{market_lower}.com",
         "Registered 2025-02-18 | Registrant: MarkMonitor / {company} Inc | Nameservers: {company_lower}.com"),
        ("{company} registers {market} domains in {country} (TechCrunch)",
         "https://techcrunch.com/2025/03/{company_lower}-{market_lower}-{country_lower}",
         "DomainIQ flagged a cluster of {market}-adjacent domains registered by {company} targeting {country}."),
    ],
    "exec_hires": [
        ("{company} hires VP {market} from leading {country} insurer (Business Insider)",
         "https://businessinsider.com/{company_lower}-vp-{market_lower}-{country_lower}",
         "{company} has recruited a veteran {market} executive to lead a new {country} vertical."),
        ("LinkedIn: Priya Mehta joins {company} as Director of {market} Strategy — {country}",
         "https://linkedin.com/in/priya-mehta-{market_lower}",
         "Previously Head of {market} Innovation at Allianz {country}. Now building new vertical at {company}."),
    ],
    "partnerships": [
        ("{company} Gold Sponsor — {market}Tech {country} Summit 2025",
         "https://{market_lower}tech{country_lower}.com/sponsors",
         "{company} CEO confirmed as keynote at {market}Tech {country} Summit 2025."),
        ("{company} and local {country} {market} leader announce alliance (Reuters)",
         "https://reuters.com/{company_lower}-{market_lower}-{country_lower}-alliance",
         "The two companies will co-develop {market} products for the {country} market, Reuters reports."),
    ],
    "patents": [
        ("US20250198734A1 — {company}: {market} risk assessment system — {country}",
         "https://patents.google.com/patent/US20250198734A1",
         "Filed Jan 2025. {market} risk scoring integrated into {company}'s payment infrastructure for {country}."),
        ("{company} files {market} patents targeting {country} regulatory framework",
         "https://patentscope.wipo.int/{company_lower}-{market_lower}",
         "Three patent applications covering {market} data processing and underwriting for {country}."),
    ],
}


def _mock_results(query: str, agent_id: str = "") -> list[dict]:
    pool = _MOCK_POOL.get(agent_id)
    if not pool:
        q = query.lower()
        if "linkedin" in q or "job" in q or "hiring" in q:
            pool = _MOCK_POOL["job_posts"]
        elif "domain" in q or "website" in q:
            pool = _MOCK_POOL["domain_regs"]
        elif "hired" in q or "vp" in q or "director" in q:
            pool = _MOCK_POOL["exec_hires"]
        elif "partner" in q or "sponsor" in q or "conference" in q:
            pool = _MOCK_POOL["partnerships"]
        elif "patent" in q or "uspto" in q:
            pool = _MOCK_POOL["patents"]
        else:
            random.seed(hash(query) % 2**32)
            pool = random.choice(list(_MOCK_POOL.values()))

    # Extract tokens from query
    words   = query.split()
    company = words[0].capitalize() if words else "Acme"
    market  = words[1].capitalize() if len(words) > 1 else "FinTech"
    country = words[2].capitalize() if len(words) > 2 else "Global"

    results = []
    for title_tpl, url_tpl, snippet_tpl in pool:
        fmt = dict(
            company=company, company_lower=company.lower(),
            market=market,   market_lower=market.lower().replace(" ", "-"),
            country=country, country_lower=country.lower().replace(" ", "-"),
        )
        results.append({
            "title":   title_tpl.format(**fmt),
            "url":     url_tpl.format(**fmt),
            "snippet": snippet_tpl.format(**fmt),
        })
    return results