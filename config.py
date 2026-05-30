import os
from dotenv import load_dotenv
load_dotenv(override=True)

OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
BRIGHTDATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY", "")
BRIGHTDATA_ZONE    = os.getenv("BRIGHTDATA_ZONE", "serp")
BRIGHTDATA_API_URL = "https://api.brightdata.com/request"
MOCK_MODE          = not BRIGHTDATA_API_KEY

OPENAI_MODEL  = "gpt-4o"
MAX_TOKENS    = 1000
SERP_RESULTS  = 10
AGENT_TIMEOUT = 25

COUNTRIES = [
    "Global","United States","United Kingdom","India","Germany",
    "France","Singapore","UAE","Brazil","Japan","Australia","Canada"
]

AGENTS = {
    "job_posts": {
        "label":"Job Posting Signals","emoji":"💼","max_score":25,
        "query_tpl":'site:linkedin.com/jobs "{company}" "{market}" "{country}"',
        "signal":"LinkedIn job postings targeting the market and country",
    },
    "domain_regs": {
        "label":"Domain Registration Signals","emoji":"🌐","max_score":25,
        "query_tpl":"{company} {market} {country} domain registration OR new website OR brand expansion",
        "signal":"newly registered domains or brand expansions into the target market",
    },
    "exec_hires": {
        "label":"Executive Hire Signals","emoji":"👤","max_score":20,
        "query_tpl":"{company} hired VP OR director OR head {market} {country}",
        "signal":"senior executive hires signalling strategic intent",
    },
    "partnerships": {
        "label":"Partnership & Conference","emoji":"🤝","max_score":15,
        "query_tpl":"{company} {market} {country} partnership OR sponsor OR conference 2025",
        "signal":"partnerships or conference appearances in the market and country",
    },
    "patents": {
        "label":"Patent & IP Signals","emoji":"📄","max_score":15,
        "query_tpl":"{company} patent {market} {country} site:patents.google.com OR site:uspto.gov",
        "signal":"patent filings in the target market domain",
    },
}

TOTAL_MAX_SCORE = sum(a["max_score"] for a in AGENTS.values())

# Local competitor agent (runs after main 5)
LOCAL_COMPETITOR_AGENT = {
    "label":     "Local Competitor Analysis",
    "emoji":     "🏆",
    "query_tpl": "top {market} companies in {country} market leaders 2025",
    "signal":    "dominant local players, their strengths, weaknesses and market share",
}

# Local competitor agent (runs after main 5)
LOCAL_COMPETITOR_AGENT = {
    "label":     "Local Competitor Analysis",
    "emoji":     "🏆",
    "query_tpl": "top {market} companies in {country} market leaders 2025",
    "signal":    "dominant local players, their strengths, weaknesses and market share",
}