import json, re
from openai import AsyncOpenAI
from config import OPENAI_MODEL, MAX_TOKENS, OPENAI_API_KEY, TOTAL_MAX_SCORE
from models import AgentResult, CompanyReport

_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def synthesize(company: str, market: str, country: str, agent_results: list[AgentResult]) -> CompanyReport:
    total       = sum(r.score for r in agent_results)
    probability = round((total / TOTAL_MAX_SCORE) * 100)
    confidence  = "high" if probability >= 70 else "medium" if probability >= 40 else "low"

    summaries = "\n".join(f"[{r.emoji} {r.label}] {r.score}/{r.max_score}: " + " | ".join(r.findings) for r in agent_results)
    prompt = f"""Senior competitive intelligence analyst. Write an executive brief.

COMPANY: {company} | MARKET: {market} | COUNTRY: {country} | SCORE: {probability}/100

AGENT FINDINGS:
{summaries}

Respond ONLY with valid JSON (no markdown):
{{"verdict":"<one sentence>","timeline":"<e.g. 3-6 months>","key_findings":["f1","f2","f3"],"strategic_implication":"<one paragraph>","recommended_actions":["a1","a2","a3"]}}"""

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

    p = probability
    return CompanyReport(
        company=company, market=market, country=country,
        probability=probability, confidence=confidence,
        timeline=data.get("timeline","Imminent" if p>=80 else "3-6 months" if p>=60 else "6-12 months" if p>=40 else "12+ months"),
        verdict=data.get("verdict",f"{'Strong' if p>=70 else 'Moderate' if p>=40 else 'Weak'} signals for {company} entering {market} in {country}."),
        key_findings=data.get("key_findings",[r.findings[0] for r in agent_results if r.findings][:5]),
        strategic_implication=data.get("strategic_implication",""),
        recommended_actions=data.get("recommended_actions",[]),
        agent_results=agent_results,
    )