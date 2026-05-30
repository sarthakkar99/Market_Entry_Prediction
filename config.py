# """
# config.py
# ---------
# All environment variables, constants, and agent registry.
# Nothing else lives here — import this everywhere.
# """

# import os
# from dotenv import load_dotenv

# load_dotenv()

# # ── API Keys ────────────────────────────────────────────────────────────────
# OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY", "")
# BRIGHTDATA_API_KEY  = os.getenv("BRIGHTDATA_API_KEY", "")
# BRIGHTDATA_ZONE     = os.getenv("BRIGHTDATA_ZONE", "serp")

# # ── Bright Data REST API ─────────────────────────────────────────────────────
# BRIGHTDATA_API_URL  = "https://api.brightdata.com/request"

# # True when Bright Data key is missing → use mock data
# MOCK_MODE = not BRIGHTDATA_API_KEY

# # ── Model ────────────────────────────────────────────────────────────────────
# OPENAI_MODEL   = "gpt-4o"
# MAX_TOKENS     = 1000
# SERP_RESULTS   = 10          # results per SERP query
# AGENT_TIMEOUT  = 20          # seconds per agent HTTP call

# # ── Agent registry ───────────────────────────────────────────────────────────
# AGENTS: dict[str, dict] = {
#     "job_posts": {
#         "label":     "Job Posting Scanner",
#         "emoji":     "💼",
#         "max_score": 25,
#         "query_tpl": "{company} hiring {market} jobs site:linkedin.com OR site:greenhouse.io OR site:lever.co",
#         "signal":    "job postings and hiring patterns for the target market",
#     },
#     "domain_regs": {
#         "label":     "Domain Registration Monitor",
#         "emoji":     "🌐",
#         "max_score": 25,
#         "query_tpl": "{company} {market} domain registration OR new website OR brand",
#         "signal":    "newly registered domains or brand expansions into the target market",
#     },
#     "exec_hires": {
#         "label":     "Executive Hire Tracker",
#         "emoji":     "👤",
#         "max_score": 20,
#         "query_tpl": "{company} hired executive {market} VP director from",
#         "signal":    "senior hires from target-market companies signalling strategic intent",
#     },
#     "partnerships": {
#         "label":     "Partnership & Conference Detector",
#         "emoji":     "🤝",
#         "max_score": 15,
#         "query_tpl": "{company} {market} partnership OR sponsor OR conference OR alliance 2025",
#         "signal":    "partnerships, sponsorships, or conference appearances in the target market",
#     },
#     "patents": {
#         "label":     "Patent & IP Monitor",
#         "emoji":     "📄",
#         "max_score": 15,
#         "query_tpl": "{company} patent {market} site:patents.google.com OR site:uspto.gov",
#         "signal":    "patent filings and R&D investment in the target market domain",
#     },
# }

# TOTAL_MAX_SCORE = sum(a["max_score"] for a in AGENTS.values())  # 100

"""
config.py
---------
All environment variables, constants, and agent registry.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ─────────────────────────────────────────────────────────────────
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
BRIGHTDATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY", "")
BRIGHTDATA_ZONE    = os.getenv("BRIGHTDATA_ZONE", "serp")
BRIGHTDATA_API_URL = "https://api.brightdata.com/request"

# True when Bright Data key is missing → use mock data
MOCK_MODE = not BRIGHTDATA_API_KEY

# ── Model ─────────────────────────────────────────────────────────────────────
OPENAI_MODEL  = "gpt-4o"
MAX_TOKENS    = 1000
SERP_RESULTS  = 10
AGENT_TIMEOUT = 25

# ── Countries ─────────────────────────────────────────────────────────────────
COUNTRIES = [
    "Global", "United States", "United Kingdom", "India", "Germany",
    "France", "Singapore", "UAE", "Brazil", "Japan", "Australia", "Canada"
]

# ── Agent registry ────────────────────────────────────────────────────────────
# query_tpl supports {company}, {market}, {country}
AGENTS: dict[str, dict] = {
    "job_posts": {
        "label":     "Job Posting Signals",
        "emoji":     "💼",
        "max_score": 25,
        "query_tpl": 'site:linkedin.com/jobs "{company}" "{market}" "{country}"',
        "signal":    "LinkedIn job postings targeting the market and country — volume and seniority of roles",
    },
    "domain_regs": {
        "label":     "Domain Registration Signals",
        "emoji":     "🌐",
        "max_score": 25,
        "query_tpl": "{company} {market} {country} domain registration OR new website OR brand expansion",
        "signal":    "newly registered domains or brand expansions into the target market and country",
    },
    "exec_hires": {
        "label":     "Executive Hire Signals",
        "emoji":     "👤",
        "max_score": 20,
        "query_tpl": "{company} hired VP OR director OR head {market} {country} from",
        "signal":    "senior executive hires from target-market companies in the target country",
    },
    "partnerships": {
        "label":     "Partnership & Conference",
        "emoji":     "🤝",
        "max_score": 15,
        "query_tpl": "{company} {market} {country} partnership OR sponsor OR conference OR alliance 2025",
        "signal":    "partnerships, sponsorships, or conference appearances in the market and country",
    },
    "patents": {
        "label":     "Patent & IP Signals",
        "emoji":     "📄",
        "max_score": 15,
        "query_tpl": "{company} patent {market} {country} site:patents.google.com OR site:uspto.gov",
        "signal":    "patent filings and R&D investment in the target market domain",
    },
}

TOTAL_MAX_SCORE = sum(a["max_score"] for a in AGENTS.values())  # 100