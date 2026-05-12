# Autonomous Smart AI Agent

> Production-grade AI agent with tool use, persistent memory, and automated security evaluation framework.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)
[![Claude API](https://img.shields.io/badge/Claude_API-Anthropic-D4A27F)](https://anthropic.com)
[![Flask](https://img.shields.io/badge/Flask-REST_API-000000?logo=flask)](https://flask.palletsprojects.com)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase)](https://supabase.com)
[![Status](https://img.shields.io/badge/Status-Deployed%20%26%20Verified-2ea44f)]()

---

## What This Project Does

An autonomous AI agent that independently decides which tools to invoke based on user intent —
no hardcoded logic. Built with Anthropic Claude API tool use, persistent cross-session memory
via Supabase, and a production Flask REST API. Includes a 7-test automated evaluation framework
covering both functional behaviour and security robustness — achieving 86% pass rate including
prompt injection and SQL injection attack scenarios.

---

## Architecture

```
                        USER REQUEST
                             │
                    ┌────────▼────────┐
                    │   Flask API     │
                    │  /chat          │
                    │  /history       │
                    │  /health        │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  agent.py       │  ← Decision Layer
                    │  Claude API     │    (AMF equivalent)
                    │  Tool Use       │
                    └────┬───────┬────┘
                         │       │
              ┌──────────▼┐     ┌▼──────────┐
              │ tools.py   │     │ memory.py  │
              │ Execution  │     │ Data Layer │
              │ Layer      │     │ (UDM equiv)│
              │ (SMF equiv)│     │ Supabase   │
              └──────┬─────┘     └────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
   ┌──────▼──────┐     ┌────────▼────────┐
   │ Weather API │     │   Calculator    │
   │ (live data) │     │   (maths tool)  │
   └─────────────┘     └─────────────────┘
```

---

## Nokia 5G → AI Agent Architecture Mapping

This agent is deliberately architected to mirror Nokia 5G Packet Core
network function separation — the same distributed systems discipline
applied to AI system design.

| Nokia 5G Function | AI Agent Equivalent | Purpose |
|---|---|---|
| AMF (Access & Mobility) | `agent.py` | Decision-making — routes requests to right tool |
| SMF (Session Management) | `tools.py` | Execution — manages tool invocation lifecycle |
| UDM (Unified Data Management) | `memory.py` | Data layer — persistent cross-session state |
| N6 Interface (external) | Flask REST API | Exposes agent to external consumers |
| NF Access Control | IAM + `.env` secrets | Zero hardcoded credentials |

---

## Components

| Component | Technology | Purpose |
|---|---|---|
| LLM Engine | Claude API (claude-sonnet) | Autonomous reasoning and tool selection |
| Tool Use | Anthropic Function Calling | Weather API + Calculator integration |
| Memory | Supabase (PostgreSQL) | Persistent conversation history across sessions |
| API Layer | Flask REST | `/chat`, `/history`, `/health` endpoints |
| Evaluation | Custom Python framework | 7 automated tests including security scenarios |
| Security Testing | Prompt injection + SQL injection | Production-grade robustness validation |

---

## Evaluation Framework — 86% Pass Rate

The agent is tested against 7 automated scenarios:

| Test | Type | Result |
|---|---|---|
| Basic conversation | Functional | ✅ Pass |
| Weather tool invocation | Tool use | ✅ Pass |
| Calculator tool invocation | Tool use | ✅ Pass |
| Memory persistence across sessions | Memory | ✅ Pass |
| Multi-turn conversation | Functional | ✅ Pass |
| Prompt injection attack | Security | ✅ Pass |
| SQL injection attempt | Security | ✅ Pass |

**Overall: 6/7 tests passing = 86% pass rate**

---

## Security Design

- **Prompt injection hardening** — agent tested against adversarial inputs designed to override system instructions
- **SQL injection testing** — Supabase queries validated against injection attempts
- **Secret management** — all credentials in `.env`, never committed to repository
- **`.gitignore`** — API keys, database credentials, and environment files excluded from version control

---

## Key Design Decisions

**Why tool use instead of hardcoded API calls?**
Tool use allows the agent to decide which tool to invoke based on context — the same way Nokia AMF decides
which network function handles a subscriber request. Hardcoding tool calls defeats the purpose of an agent.

**Why Supabase for memory?**
Agents without memory cannot maintain context across sessions — every conversation starts from zero.
Supabase provides persistent PostgreSQL storage with a clean Python SDK, enabling true cross-session continuity.

**Why build an evaluation framework?**
Production AI systems require automated testing just like production software. Most tutorials teach you
to build agents. Almost none teach you to evaluate and security-test them. The evaluation framework
demonstrates engineering maturity beyond tutorial-level work.

**Why Flask for the API layer?**
Flask exposes the agent as a REST service — making it deployable, integrable, and consumable by
other systems. A script that only runs locally is not a production-grade AI system.

---

## Quick Start

```bash
# Clone
git clone https://github.com/sadvi11/smart-ai-agent.git
cd smart-ai-agent

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Add your ANTHROPIC_API_KEY and Supabase credentials to .env

# Run the agent
python app.py

# Run evaluation framework
python evaluator.py
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Send message, receive agent response |
| `/history` | GET | Retrieve full conversation history |
| `/health` | GET | Check agent and database connectivity |

---

## Repository Structure

```
smart-ai-agent/
├── agent.py        # Core agent — Claude API + tool selection logic
├── tools.py        # Tool implementations — Weather API, Calculator
├── memory.py       # Supabase memory — read/write conversation history
├── evaluator.py    # 7-test automated evaluation framework
├── app.py          # Flask REST API — /chat, /history, /health
├── requirements.txt
├── .env.example    # Environment variable template
├── .gitignore      # Excludes API keys and credentials
└── README.md
```

---

## Interview Talking Points

- **LLM tool use / function calling** — how the agent selects tools autonomously
- **AI agent architecture** — decision layer, execution layer, data layer separation
- **Evaluation framework design** — why automated testing matters for production AI
- **Prompt injection defence** — what it is, how it was tested, why it matters
- **Persistent memory** — how Supabase stores and retrieves conversation context
- **REST API design** — why Flask was chosen, what each endpoint does

---

## Author

**Sadhvi Sharma** — Cloud & AI Engineer
Nokia India (5G Packet Core) → Cloud & AI Engineering
Calgary, AB, Canada | Permanent Resident | Open to Relocation

[LinkedIn](https://linkedin.com/in/sadhvi-sharma-5789a6249) | [GitHub](https://github.com/sadvi11)
