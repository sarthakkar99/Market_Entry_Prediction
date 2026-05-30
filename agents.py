import asyncio, json, re
from openai import AsyncOpenAI
from config  import AGENTS, OPENAI_MODEL, MAX_TOKENS, OPENAI_API_KEY
from scraper import fetch_serp
from models  import AgentResult

_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def run_all_agents(company: str, market: str, country: str) -> list[AgentResult]:
    tasks = [_run_agent(aid, company, market, country) for aid in AGENTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [_fallback(aid, str(r)) if isinstance(r, Exception) else r for aid, r in zip(AGENTS.keys(), results)]

async def _run_agent(agent_id: str, company: str, market: str, country: str) -> AgentResult:
    cfg   = AGENTS[agent_id]
    query = cfg["query_tpl"].format(company=company, market=market, country=country)
    serp  = await fetch_serp(query, agent_id)
    text  = "\n\n".join(f"{i+1}. {r['title']}\n   {r['url']}\n   {r['snippet']}" for i,r in enumerate(serp)) or "No results."
    prompt = f"""You are a competitive intelligence analyst.
Analyse these search results for evidence that {company} is entering the {market} market in {country}.
Focus on: {cfg["signal"]}.

RESULTS:
{text}

Score 0-{cfg["max_score"]} based on signal strength.
Respond ONLY with valid JSON (no markdown):
{{"score":<int>,"findings":["finding1","finding2","finding3"],"reasoning":"<one paragraph>","sources":["url1","url2"]}}"""

    resp = await _openai.chat.completions.create(
        model=OPENAI_MODEL, max_tokens=MAX_TOKENS, temperature=0, seed=42,
        messages=[{"role":"user","content":prompt}]
    )
    raw = resp.choices[0].message.content
    try:
        data = json.loads(raw.strip())
    except:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group()) if m else {}

    return AgentResult(
        agent_id=agent_id, label=cfg["label"], emoji=cfg["emoji"],
        score=max(0,min(cfg["max_score"],int(data.get("score",0)))),
        max_score=cfg["max_score"],
        findings=data.get("findings",["No findings."]),
        reasoning=data.get("reasoning",""),
        sources=data.get("sources",[r["url"] for r in serp[:2]]),
    )

def _fallback(agent_id: str, error: str) -> AgentResult:
    cfg = AGENTS[agent_id]
    return AgentResult(agent_id=agent_id,label=cfg["label"],emoji=cfg["emoji"],
        score=0,max_score=cfg["max_score"],findings=[f"Error: {error}"],reasoning="",sources=[])


async def run_competitor_analysis(company: str, market: str, country: str, is_loser: bool) -> dict:
    """Find local competitors and generate winning strategy for losers."""
    from config import LOCAL_COMPETITOR_AGENT
    cfg   = LOCAL_COMPETITOR_AGENT
    query = cfg["query_tpl"].format(company=company, market=market, country=country)
    serp  = await fetch_serp(query, "local_competitors")
    text  = "\n\n".join(f"{i+1}. {r['title']}\n   {r['url']}\n   {r['snippet']}" for i,r in enumerate(serp)) or "No results."

    loser_instruction = f"""
Also, since {company} currently has a LOWER market entry score than its competitors,
provide a specific WINNING STRATEGY section explaining exactly how {company} can:
1. Exploit weaknesses of local players
2. Differentiate from both local AND foreign competitors
3. What to prioritize in the first 6 months to rapidly close the gap
""" if is_loser else ""

    prompt = f"""You are a competitive intelligence analyst specializing in market entry strategy.

TASK: Analyze the top local competitors in the {market} market in {country} that {company} would face.

SEARCH RESULTS:
{text}

{loser_instruction}

Respond ONLY with valid JSON (no markdown):
{{
  "competitors": [
    {{"name":"<company name>","strengths":["s1","s2"],"weaknesses":["w1","w2"]}},
    {{"name":"<company name>","strengths":["s1","s2"],"weaknesses":["w1","w2"]}},
    {{"name":"<company name>","strengths":["s1","s2"],"weaknesses":["w1","w2"]}}
  ],
  "winning_strategy": "<detailed paragraph on how {company} specifically can beat these locals — or empty string if not a loser>"
}}"""

    resp = await _openai.chat.completions.create(
        model=OPENAI_MODEL, max_tokens=MAX_TOKENS, temperature=0, seed=42,
        messages=[{"role":"user","content":prompt}]
    )
    raw = resp.choices[0].message.content
    try:
        return json.loads(raw.strip())
    except:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        try:    return json.loads(m.group()) if m else {}
        except: return {}