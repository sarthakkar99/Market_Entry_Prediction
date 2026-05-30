import httpx
import random
from urllib.parse import quote_plus
from config import BRIGHTDATA_API_KEY, BRIGHTDATA_API_URL, BRIGHTDATA_ZONE, MOCK_MODE, SERP_RESULTS, AGENT_TIMEOUT

async def fetch_serp(query: str, agent_id: str = "") -> list[dict]:
    if MOCK_MODE:
        return _mock(query, agent_id)
    try:
        return await _brightdata(query)
    except Exception as exc:
        print(f"[scraper] Bright Data error ({exc}), falling back to mock")
        return _mock(query, agent_id)

async def _brightdata(query: str) -> list[dict]:
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {BRIGHTDATA_API_KEY}"}
    payload = {"zone":BRIGHTDATA_ZONE,"url":f"https://www.google.com/search?q={quote_plus(query)}&num={SERP_RESULTS}&brd_json=1","format":"raw"}
    async with httpx.AsyncClient(timeout=AGENT_TIMEOUT) as client:
        resp = await client.post(BRIGHTDATA_API_URL, headers=headers, json=payload)
        resp.raise_for_status()
    data = resp.json()
    return [{"title":i.get("title",""),"url":i.get("link",""),"snippet":i.get("description","")} for i in data.get("organic",[])[:SERP_RESULTS]]

_POOL = {
    "job_posts":[
        ("{company} | Head of {market} Products | {country}","https://linkedin.com/jobs/1","{company} seeks Head of {market} in {country}. 7+ yrs experience required."),
        ("{company} | {market} Compliance Manager | {country}","https://linkedin.com/jobs/2","Build {company}'s {market} compliance in {country}. Reports to VP New Verticals."),
        ("{company} | {market} Business Development | {country}","https://linkedin.com/jobs/3","Drive {company}'s {market} go-to-market in {country}."),
    ],
    "domain_regs":[
        ("{company_lower}{market_lower}.com WHOIS","https://whois.domaintools.com/{company_lower}{market_lower}.com","Registered 2025-02 | Registrant: {company} Inc | Status: active"),
        ("{company} registers {market} domains in {country}","https://techcrunch.com/{company_lower}-domains","DomainIQ flagged {market} domains registered by {company} for {country}."),
    ],
    "exec_hires":[
        ("{company} hires VP {market} from {country} firm","https://linkedin.com/in/exec-1","{company} recruited a veteran {market} exec to lead {country} vertical."),
        ("Priya Mehta joins {company} as Director {market} — {country}","https://linkedin.com/in/exec-2","Previously Head of {market} at Allianz {country}. Now at {company}."),
    ],
    "partnerships":[
        ("{company} Gold Sponsor — {market}Tech {country} 2025","https://{market_lower}tech.com/sponsors","{company} CEO keynote at {market}Tech {country} Summit 2025."),
        ("{company} and {country} {market} leader announce alliance","https://reuters.com/{company_lower}-alliance","Co-develop {market} products for {country} market."),
    ],
    "patents":[
        ("US20250198734 — {company}: {market} risk assessment","https://patents.google.com/patent/US20250198734","{market} risk scoring in {company}'s infrastructure for {country}."),
        ("{company} files {market} patents for {country}","https://patentscope.wipo.int/{company_lower}","Three patents covering {market} data processing for {country}."),
    ],
}

def _mock(query: str, agent_id: str = "") -> list[dict]:
    pool = _POOL.get(agent_id)
    if not pool:
        random.seed(hash(query) % 2**32)
        pool = random.choice(list(_POOL.values()))
    words   = query.replace('"','').split()
    company = words[0].capitalize() if words else "Acme"
    market  = words[1].capitalize() if len(words) > 1 else "FinTech"
    country = words[2].capitalize() if len(words) > 2 else "Global"
    fmt = dict(company=company,company_lower=company.lower(),market=market,market_lower=market.lower(),country=country,country_lower=country.lower())
    return [{"title":t.format(**fmt),"url":u.format(**fmt),"snippet":s.format(**fmt)} for t,u,s in pool]