# Market Entry Predictor — Full Documentation
## Architecture, Business Logic, Code Walkthrough & Error History

---

## 1. WHAT THE APP DOES (Business Logic)

**Problem it solves:**
A company (e.g. Stripe) wants to enter a new market (e.g. Insurance in India).
Traditionally you'd hire analysts for weeks. This app does it in 60 seconds.

**How it works:**
1. You input up to 3 companies, a target market, and a country
2. 5 AI agents run in parallel — each looking for a different "signal" that a company is preparing to enter that market
3. Each agent searches the web, scores what it finds (0-25 or 0-20 points)
4. Scores combine into a 0-100 "Market Entry Probability"
5. OpenAI synthesizes all findings into an executive brief
6. For losing companies — a local competitor analysis shows who they'd face and how to win

**Real world use case:**
- A VC firm wants to know if Stripe is about to disrupt their insurance portfolio
- A startup wants to know if Google is entering their space before they raise money
- A corporate strategy team compares 3 competitors' likelihood of entering a new country

---

## 2. SYSTEM ARCHITECTURE

```
Browser (index.html)
    │
    │  POST /api/analyze  {companies, target_market, country}
    │  ← SSE stream (data: {...}\n\n)
    │
FastAPI (main.py)
    │
    ├── asyncio.gather → run all companies in parallel
    │       │
    │       ├── agents.py → run_all_agents(company, market, country)
    │       │       │
    │       │       ├── Agent 1: job_posts    → scraper.py → OpenAI
    │       │       ├── Agent 2: domain_regs  → scraper.py → OpenAI
    │       │       ├── Agent 3: exec_hires   → scraper.py → OpenAI
    │       │       ├── Agent 4: partnerships → scraper.py → OpenAI
    │       │       └── Agent 5: patents      → scraper.py → OpenAI
    │       │
    │       └── synthesis.py → OpenAI → CompanyReport
    │
    └── run_competitor_analysis (losers only)
            │
            └── scraper.py → OpenAI → {competitors, winning_strategy}
```

---

## 3. FILE BY FILE — LINE BY LINE

---

### config.py — The Single Source of Truth

```python
load_dotenv(override=True)
```
Loads .env file. `override=True` is CRITICAL — without it, if OPENAI_API_KEY
is already set as a Windows environment variable, it ignores your .env file.
THIS WAS A KEY BUG WE HIT.

```python
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
BRIGHTDATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY", "")
```
Reads keys from .env. Default is empty string so app doesn't crash if missing.

```python
MOCK_MODE = not BRIGHTDATA_API_KEY
```
If no Bright Data key → use fake data. App always works, even without API keys.

```python
OPENAI_MODEL = "gpt-4o"
MAX_TOKENS   = 1000
SERP_RESULTS = 10
AGENT_TIMEOUT = 25
```
Constants used everywhere. Changing model here changes it for all agents.

```python
AGENTS = {
    "job_posts": {
        "label":     "Job Posting Signals",
        "emoji":     "💼",
        "max_score": 25,
        "query_tpl": 'site:linkedin.com/jobs "{company}" "{market}" "{country}"',
        "signal":    "LinkedIn job postings...",
    },
    ...
}
```
Agent registry. Each agent has:
- `label` → shown in UI
- `max_score` → how many points it can contribute (all add to 100)
- `query_tpl` → the Google search query template with {company}, {market}, {country} placeholders
- `signal` → what Claude looks for in results

Score breakdown: job_posts(25) + domain_regs(25) + exec_hires(20) + partnerships(15) + patents(15) = 100

```python
LOCAL_COMPETITOR_AGENT = {...}
```
6th agent — runs AFTER the main 5, only for loser companies.

---

### models.py — Data Shapes (Pydantic)

```python
class AnalyzeRequest(BaseModel):
    companies:     list[str]
    target_market: str
    country:       str = Field(default="Global")

    @field_validator("companies")
    def validate_companies(cls, v):
        return [c.strip() for c in v if c.strip()][:3]
```
What the frontend sends. `field_validator` was needed because:
- Pydantic v2 doesn't accept `min_length` on lists (only strings)
- THIS WAS BUG #3 — caused 422 errors until fixed

```python
class AgentResult(BaseModel):
    agent_id, label, emoji, score, max_score,
    findings, reasoning, sources
```
What each of the 5 agents returns. `findings` = list of bullet points shown in UI.

```python
class LocalCompetitor(BaseModel):
    name, strengths, weaknesses
```
One local competitor with tagged strengths/weaknesses shown in the UI.

```python
class CompanyReport(BaseModel):
    ...
    local_competitors: list[LocalCompetitor] = []
    winning_strategy:  str = ""
    is_loser:          bool = False
```
Full report for one company. `is_loser` triggers the winning strategy section.

---

### scraper.py — Web Data Fetcher

```python
async def fetch_serp(query: str, agent_id: str = "") -> list[dict]:
    if MOCK_MODE:
        return _mock(query, agent_id)
    try:
        return await _brightdata(query)
    except Exception as exc:
        print(f"[scraper] Bright Data error ({exc}), falling back to mock")
        return _mock(query, agent_id)
```
Main function. Three paths:
1. No Bright Data key → mock immediately
2. Has key → try real API
3. Real API fails → fall back to mock (graceful degradation)

```python
async def _brightdata(query: str) -> list[dict]:
    payload = {
        "zone":   BRIGHTDATA_ZONE,
        "url":    f"https://www.google.com/search?q={quote_plus(query)}&brd_json=1",
        "format": "raw",
    }
```
Bright Data REST API call. `brd_json=1` tells Bright Data to parse the Google
HTML and return structured JSON instead of raw HTML.
BUG WE HIT: payload format was wrong (missing zone, wrong format value) → 400 errors.

```python
_POOL = {
    "job_posts": [...],
    "domain_regs": [...],
    ...
}
```
Mock data templates. Each pool has 2-4 realistic-looking results.
The `{company}`, `{market}`, `{country}` placeholders get filled at runtime.

---

### agents.py — The 5 Signal Agents

```python
async def run_all_agents(company, market, country) -> list[AgentResult]:
    tasks = [_run_agent(aid, company, market, country) for aid in AGENTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```
Runs all 5 agents simultaneously using asyncio. Total time = slowest agent,
not sum of all agents. If one fails, `return_exceptions=True` catches it
and returns a fallback instead of crashing everything.

```python
async def _run_agent(agent_id, company, market, country):
    query = cfg["query_tpl"].format(company=company, market=market, country=country)
    serp  = await fetch_serp(query, agent_id)
    ...
    resp = await _openai.chat.completions.create(
        model=OPENAI_MODEL, temperature=0, seed=42, ...
    )
```
One agent's full flow:
1. Build search query from template
2. Fetch results (real or mock)
3. Send to OpenAI with a scoring prompt
`temperature=0, seed=42` = deterministic output (same input → same score every time)
BUG WE HIT: without seed, scores changed every run.

```python
prompt = f"""...
Score 0-{cfg["max_score"]} based on signal strength.
Respond ONLY with valid JSON (no markdown):
{{"score":<int>,"findings":[...],"reasoning":"...","sources":[...]}}"""
```
The prompt tells OpenAI exactly what to look for and forces JSON output.
`ONLY valid JSON` prevents OpenAI from wrapping response in ```json blocks.

```python
async def run_competitor_analysis(company, market, country, is_loser):
```
6th agent, only called from main.py after scores are known.
`is_loser=True` adds extra instructions to the prompt asking for winning strategy.

---

### synthesis.py — Final Report Generator

```python
async def synthesize(company, market, country, agent_results):
    total       = sum(r.score for r in agent_results)
    probability = round((total / TOTAL_MAX_SCORE) * 100)
    confidence  = "high" if probability >= 70 else "medium" if probability >= 40 else "low"
```
Simple math: total score / 100 = probability percentage.
Confidence thresholds: 70%+ = high, 40-70% = medium, <40% = low.

```python
summaries = "\n".join(
    f"[{r.emoji} {r.label}] {r.score}/{r.max_score}: " + " | ".join(r.findings)
    for r in agent_results
)
```
Compresses all 5 agent findings into a single string for the synthesis prompt.
This keeps the context window small while giving OpenAI all the key facts.

---

### main.py — FastAPI Server & SSE Stream

```python
@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    return StreamingResponse(
        _stream(req.companies, req.target_market, req.country),
        media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"},
    )
```
SSE (Server-Sent Events) = one-way stream from server to browser.
`X-Accel-Buffering: no` prevents nginx from buffering the stream.
`Cache-Control: no-cache` prevents browser caching.

```python
async def _stream(companies, market, country):
    yield _e({"type":"start", ...})

    async def analyze_one(company):
        agents = await run_all_agents(company, market, country)
        report = await synthesize(company, market, country, agents)
        return company, agents, report

    results = await asyncio.gather(*[analyze_one(c) for c in companies])
```
All companies analyzed in parallel. For 3 companies with 5 agents each =
15 OpenAI calls happening simultaneously. Total time ~10-15 seconds.

```python
    winner = max(results, key=lambda x: x[2].probability)[0]

    comp_tasks = [
        run_competitor_analysis(company, market, country, is_loser=(company != winner))
        for company, _, _ in results
    ]
```
Winner = highest probability company. Losers get `is_loser=True` which
triggers the winning strategy section in the competitor analysis.

```python
def _e(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
```
SSE format. MUST end with double newline `\n\n`. The browser EventSource
API splits on this to detect message boundaries.

---

### index.html — Frontend

```javascript
let running = false;
let reportData = {};
```
Global state. `running` prevents double-clicks. `reportData` stores results
for the export function.

```javascript
function startAnalysis() {
    if (running) return;    // prevent double submission
    const cos = companies();
    ...
    fetch("/api/analyze", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({companies: cos, target_market: market, country: country})
    }).then(async resp => {
        const reader = resp.body.getReader();  // ReadableStream
        ...
        while(true) {
            const {done, value} = await reader.read();
            if (done) break;
            buf += dec.decode(value, {stream: true});
            // Split by newlines, parse each "data: {...}" line
        }
    })
}
```
Uses `fetch` + `ReadableStream` instead of `EventSource` because
EventSource only supports GET requests. We need POST to send the body.

```javascript
function handle(ev) {
    switch(ev.type) {
        case "agent_complete": // update agent card
        case "company_complete": // update gauge + report
        case "competitor_analysis": // update competitor card
        case "complete": // highlight winner, re-enable button
    }
}
```
Single event dispatcher. Each SSE event type maps to a UI update.

```javascript
function buildCol(company, market, country) {
    // Creates HTML for one company column:
    // - company header with gauge
    // - 5 agent cards
    // - report section
    // - competitor card
}
```
Called once per company when Run Analysis is clicked.
Uses `id="ac-${company}-${agentId}"` pattern so events can find
the right element: `document.getElementById("ac-Stripe-job_posts")`.

---

## 4. SSE EVENT FLOW

```
Server sends:          Frontend receives:
─────────────────────────────────────────
{type:"start"}      →  setProgress(0)
{type:"agent_complete",
 company:"Stripe",
 agent_id:"job_posts",
 data:{score,findings}}  →  updateAgentCard()
... (14 more agent_complete events)
{type:"company_complete",
 company:"Stripe",
 data:{probability, verdict...}}  →  animateGauge(), showReport()
... (2 more company_complete events)
{type:"competitor_analysis",
 company:"HDFC",
 is_loser:true,
 data:{competitors, winning_strategy}}  →  showCompetitorCard()
{type:"complete"}    →  highlightWinner(), finish()
```

---

## 5. COMPLETE BUG HISTORY

### Bug 1 — Wrong route name
**Error:** `404 Not Found` on POST
**Cause:** Frontend calling `/api/analyze`, backend had `/analyze`
**Fix:** Changed `@app.post("/analyze")` to `@app.post("/api/analyze")`

### Bug 2 — Field name mismatch
**Error:** `422 Unprocessable Content`
**Cause:** Frontend sent `target_market`, backend model had `market`
**Fix:** Renamed field in `models.py` to `target_market`

### Bug 3 — Pydantic v2 list validation
**Error:** `422 Unprocessable Content`
**Cause:** Used `min_length=1` on a `list[str]` field — only valid for strings
**Fix:** Used `@field_validator` instead

### Bug 4 — Agent ID mismatch
**Error:** Agents showed IDLE, only 2/5 updating
**Cause:** Backend used `jobs/domains/execs`, frontend expected `job_posts/domain_regs/exec_hires`
**Fix:** Renamed keys in `config.py` AGENTS dict

### Bug 5 — Old synthesis.py imported FinalReportEvent
**Error:** `ImportError: cannot import name 'FinalReportEvent'`
**Cause:** Stale local file from old session, class was renamed to `CompanyReport`
**Fix:** Replace all local files with latest versions

### Bug 6 — Windows file encoding
**Error:** `UnicodeDecodeError: 'charmap' codec`
**Cause:** `open("index.html")` uses Windows cp1252 encoding by default
**Fix:** `open("index.html", encoding="utf-8")`

### Bug 7 — Browser cache serving old HTML
**Error:** `document.getElementById('c1')` returning null
**Cause:** Browser cached old index.html with `id="company"` not `id="c1"`
**Fix:** Added `Cache-Control: no-store` headers, hard refresh (Ctrl+Shift+R)

### Bug 8 — Windows env var override
**Error:** Wrong OpenAI API key being used despite correct .env
**Cause:** `load_dotenv()` doesn't override existing Windows env vars
**Fix:** Changed to `load_dotenv(override=True)` in config.py

### Bug 9 — Bright Data 400 errors
**Error:** `400 Bad Request` on every Bright Data call
**Cause:** Wrong payload format — missing `zone` field, wrong `format` value
**Fix:** Added `"zone": BRIGHTDATA_ZONE`, changed `"format": "raw"`
**Status:** Still failing — app falls back to mock data gracefully

### Bug 10 — asyncio gather never awaited
**Error:** Agents stuck on IDLE, coroutine never awaited warning
**Cause:** `asyncio.create_task(asyncio.gather(*coroutines))` — task created but result never consumed
**Fix:** Simplified to `await asyncio.gather(*[analyze_one(c) for c in companies])`

### Bug 11 — Scraper missing agent_id parameter
**Error:** `TypeError: fetch_serp() takes 1 positional argument but 2 were given`
**Cause:** Local scraper.py had old signature without `agent_id` parameter
**Fix:** Added `agent_id: str = ""` parameter to `fetch_serp()`

### Bug 12 — _run_agent missing country parameter
**Error:** `TypeError: _run_agent() takes 3 positional arguments but 4 were given`
**Cause:** Local agents.py had old signature without `country` parameter
**Fix:** Added `country: str` to `_run_agent()` signature and query builder

---

## 6. HOW DATA FLOWS END TO END

```
User types: "Stripe" + "Insurance" + "India"
                │
                ▼
    Frontend builds JSON:
    {companies:["Stripe"], target_market:"Insurance", country:"India"}
                │
                ▼
    POST /api/analyze → FastAPI validates with AnalyzeRequest model
                │
                ▼
    _stream() generator starts yielding SSE events
                │
                ▼
    analyze_one("Stripe") called:
        ├── run_all_agents("Stripe","Insurance","India")
        │       ├── query = 'site:linkedin.com/jobs "Stripe" "Insurance" "India"'
        │       ├── fetch_serp(query, "job_posts") → [mock results]
        │       ├── OpenAI prompt: "Score these results 0-25..."
        │       └── AgentResult(score=18, findings=["Stripe hiring..."])
        │
        └── synthesize("Stripe", "Insurance", "India", [5 AgentResults])
                ├── probability = (18+20+12+10+11) / 100 * 100 = 71%
                ├── confidence = "high"
                └── OpenAI: "Write executive brief..."
                │
                ▼
    SSE events yielded:
        data: {"type":"agent_complete","company":"Stripe","agent_id":"job_posts",...}
        data: {"type":"company_complete","company":"Stripe","data":{"probability":71,...}}
                │
                ▼
    Frontend receives chunk → parses "data: {...}" lines → handle(ev)
        → animateGauge("Stripe", 71)
        → showReport(findings, verdict, actions)
```

---

## 7. CURRENT STATUS

| Component | Status |
|-----------|--------|
| FastAPI server | ✅ Running |
| SSE streaming | ✅ Working |
| Mock data | ✅ Working |
| OpenAI scoring | ✅ Working (after API key fix) |
| Bright Data real scraping | ❌ 400 errors (payload format issue) |
| Multi-company comparison | ✅ Working |
| Country filtering | ✅ Working |
| Competitor analysis | ✅ Built, needs testing |
| Winner badge | ✅ Working |
| Export brief | ✅ Working |

---
