"""
synthesis.py
------------
Final Claude synthesis for one company's agent results.
"""

import json
from openai import AsyncOpenAI

from config import OPENAI_MODEL, MAX_TOKENS, OPENAI_API_KEY, TOTAL_MAX_SCORE
from models import AgentResult, CompanyReport

_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def synthesize(
    company: str,
    market:  str,
    country: str,
    agent_results: list[AgentResult],
) -> CompanyReport:

    total_score = sum(r.score for r in agent_results)
    probability = round((total_score / TOTAL_MAX_SCORE) * 100)
    confidence  = "high" if probability >= 70 else "medium" if probability >= 40 else "low"

    prompt = _build_prompt(company, market, country, agent_results, probability)
    raw    = await _call_openai(prompt)
    report = _parse(raw)

    return CompanyReport(
        company               = company,
        market                = market,
        country               = country,
        score                 = total_score,
        probability           = probability,
        confidence            = confidence,
        timeline              = report.get("timeline", _default_timeline(probability)),
        verdict               = report.get("verdict",  _default_verdict(probability, company, market, country)),
        key_findings          = report.get("key_findings", _top_findings(agent_results)),
        strategic_implication = report.get("strategic_implication", ""),
        recommended_actions   = report.get("recommended_actions", []),
        agent_results         = agent_results,
    )


def _build_prompt(company, market, country, results, probability):
    summaries = "\n\n".join(
        f"[{r.emoji} {r.label}] {r.score}/{r.max_score}\n"
        + "\n".join(f"  • {f}" for f in r.findings)
        for r in results
    )
    return f"""You are a senior competitive intelligence analyst.

COMPANY: {company}  |  MARKET: {market}  |  COUNTRY: {country}
COMPOSITE SCORE: {probability}/100

AGENT FINDINGS
{summaries}

Write an executive intelligence brief. Be specific about {country}-specific signals.

OUTPUT — valid JSON only, no markdown fences:
{{
  "verdict":               "<one sentence assessment>",
  "timeline":              "<entry timeline e.g. '3–6 months' or 'Already entered'>",
  "key_findings":          ["<finding 1>", "<finding 2>", "<finding 3>"],
  "strategic_implication": "<one paragraph on what this means for {country} competitors/investors>",
  "recommended_actions":   ["<action 1>", "<action 2>", "<action 3>"]
}}"""


async def _call_openai(prompt: str) -> str:
    resp = await _openai.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=MAX_TOKENS,
        temperature=0,
        seed=42,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


def _parse(raw: str) -> dict:
    try:
        return json.loads(raw.strip())
    except Exception:
        import re
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        try:    return json.loads(m.group()) if m else {}
        except: return {}


def _default_timeline(p):
    if p >= 80: return "Imminent — 1–3 months"
    if p >= 60: return "Near-term — 3–6 months"
    if p >= 40: return "Medium-term — 6–12 months"
    return "Long-term or speculative — 12+ months"

def _default_verdict(p, company, market, country):
    if p >= 70: return f"Strong evidence {company} is actively preparing to enter {market} in {country}."
    if p >= 40: return f"Moderate signals suggest {company} is exploring {market} entry in {country}."
    return f"Weak signals only — {company} entry into {market} in {country} remains speculative."

def _top_findings(results):
    findings = []
    for r in results:
        if r.findings: findings.append(r.findings[0])
    return findings[:5]