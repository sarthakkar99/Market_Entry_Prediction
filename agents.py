"""
agents.py
---------
Five async signal agents. Each agent:
  1. Builds a targeted search query (with company, market, country)
  2. Fetches SERP results — LinkedIn-targeted for job_posts agent
  3. Sends results to OpenAI for scoring + analysis
  4. Returns an AgentResult
"""

import asyncio
import json
from openai import AsyncOpenAI

from config  import AGENTS, OPENAI_MODEL, MAX_TOKENS, OPENAI_API_KEY
from scraper import fetch_serp
from models  import AgentResult

_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)


# ── Public entry point ────────────────────────────────────────────────────────

async def run_all_agents(company: str, market: str, country: str) -> list[AgentResult]:
    tasks = [
        _run_agent(agent_id, company, market, country)
        for agent_id in AGENTS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [
        _fallback_result(aid, str(r)) if isinstance(r, Exception) else r
        for aid, r in zip(AGENTS.keys(), results)
    ]


# ── Single agent ──────────────────────────────────────────────────────────────
async def _run_agent(agent_id: str, company: str, market: str, country: str) -> AgentResult:
    cfg   = AGENTS[agent_id]
    query = cfg["query_tpl"].format(company=company, market=market, country=country)

    serp_results = await fetch_serp(query, agent_id)
    serp_text    = _format_serp(serp_results)
    prompt = _build_prompt(company, market, country, cfg, serp_text)
    raw          = await _call_openai(prompt)
    return _parse_response(agent_id, cfg, raw, serp_results)


# ── OpenAI call ───────────────────────────────────────────────────────────────

async def _call_openai(prompt: str) -> str:
    resp = await _openai.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=MAX_TOKENS,
        temperature=0,
        seed=42,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


# ── Prompt ────────────────────────────────────────────────────────────────────

def _build_prompt(company: str, market: str, country: str, cfg: dict, serp_text: str) -> str:
    return f"""You are a competitive intelligence analyst.

TASK
Analyse the search results below for evidence that **{company}** is preparing
to enter the **{market}** market in **{country}**.
Focus specifically on: {cfg["signal"]}.

SEARCH RESULTS
{serp_text}

SCORING
Award a score from 0 to {cfg["max_score"]}:
  0                        = no evidence
  1–{cfg["max_score"]//3}  = weak / speculative
  {cfg["max_score"]//3}–{2*cfg["max_score"]//3} = moderate / credible
  {2*cfg["max_score"]//3}–{cfg["max_score"]}     = strong / near-certain

OUTPUT — valid JSON only, no markdown fences:
{{
  "score":     <int 0–{cfg["max_score"]}>,
  "findings":  ["<finding 1>", "<finding 2>", "<finding 3>"],
  "reasoning": "<one paragraph>",
  "sources":   ["<url 1>", "<url 2>"]
}}"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_serp(results: list[dict]) -> str:
    if not results:
        return "No results found."
    return "\n\n".join(
        f"{i}. {r['title']}\n   {r['url']}\n   {r['snippet']}"
        for i, r in enumerate(results, 1)
    )


def _parse_response(agent_id, cfg, raw, serp_results) -> AgentResult:
    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError:
        import re
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group()) if m else {}

    return AgentResult(
        agent_id  = agent_id,
        label     = cfg["label"],
        emoji     = cfg["emoji"],
        score     = max(0, min(cfg["max_score"], int(data.get("score", 0)))),
        max_score = cfg["max_score"],
        findings  = data.get("findings", ["No findings."]),
        reasoning = data.get("reasoning", "Analysis unavailable."),
        sources   = data.get("sources", [r["url"] for r in serp_results[:2]]),
    )


def _fallback_result(agent_id: str, error: str) -> AgentResult:
    cfg = AGENTS[agent_id]
    return AgentResult(
        agent_id=agent_id, label=cfg["label"], emoji=cfg["emoji"],
        score=0, max_score=cfg["max_score"],
        findings=[f"Agent failed: {error}"],
        reasoning="Error during analysis.", sources=[],
    )