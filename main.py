import json, asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from models    import AnalyzeRequest
from agents    import run_all_agents
from synthesis import synthesize
from config    import AGENTS, MOCK_MODE

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", encoding="utf-8") as f:
        content = f.read()
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=content, headers={
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    })

@app.get("/health")
async def health():
    return {"status":"ok","mock_mode":MOCK_MODE}

@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    return StreamingResponse(
        _stream(req.companies, req.target_market, req.country),
        media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"},
    )

async def _stream(companies: list[str], market: str, country: str):
    try:
        yield _e({"type":"start","companies":companies,"market":market,"country":country})

        async def analyze_one(company):
            agents = await run_all_agents(company, market, country)
            report = await synthesize(company, market, country, agents)
            return company, agents, report

        results = await asyncio.gather(*[analyze_one(c) for c in companies])

        for company, agents, report in results:
            for r in agents:
                pct = round((r.score/r.max_score)*100) if r.max_score else 0
                strength = "strong" if pct>=70 else "moderate" if pct>=40 else "weak"
                yield _e({
                    "type":"agent_complete","company":company,"agent_id":r.agent_id,
                    "data":{"score":r.score,"max_score":r.max_score,"results_found":len(r.findings),"strength":strength,"evidence":r.findings,"sources":r.sources}
                })
            yield _e({
                "type":"company_complete","company":company,
                "data":{"probability":report.probability,"confidence":report.confidence,"timeline":report.timeline,
                        "verdict":report.verdict,"key_findings":report.key_findings,
                        "strategic_implication":report.strategic_implication,"recommended_actions":report.recommended_actions}
            })

        yield _e({"type":"complete"})

    except Exception as exc:
        yield _e({"type":"error","message":str(exc)})

def _e(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)