# Smart AI Agent

> An autonomous Claude agent that decides which tool to call, grounds its answers in a pgvector knowledge base, remembers past sessions, and is graded by an automated suite that includes prompt-injection and SQL-injection attacks.

[![CI](https://github.com/sadvi11/smart-ai-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/sadvi11/smart-ai-agent/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Haiku%204.5-D4A27F?logo=anthropic&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-REST%20API-000000?logo=flask&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-pgvector-3ECF8E?logo=supabase&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

Most "AI agent" projects are one API call in a wrapper. The part worth building is
everything around the call: deciding *whether* to use a tool, retrieving context
before answering, keeping state across sessions — and then proving it holds up when
someone attacks it.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Reasoning | Claude Haiku 4.5 (`anthropic` SDK) | Tool-use decisions are cheap and frequent; Haiku keeps latency and cost down |
| Tool use | Native Anthropic tool calling | The model picks the tool — no keyword routing or intent classifier |
| Retrieval | `sentence-transformers` (`all-MiniLM-L6-v2`) + pgvector | Embeddings computed locally, so no per-query embedding cost |
| Vector store | Supabase (Postgres + pgvector) | One managed service for both vectors and conversation history |
| Memory | Supabase `conversations` table | Sessions survive process restarts |
| API | Flask + flask-cors | Small surface; the agent is the product, not the framework |
| Evaluation | Custom harness (`evaluator.py`) | Functional *and* adversarial cases, run on demand |

## Architecture

```mermaid
flowchart TB
    Client([Client]) -->|POST /chat| API[Flask API<br/>app.py]

    API -->|load prior turns| MEM[(Supabase<br/>conversations)]
    API --> AGENT[Agent loop<br/>agent.py]

    AGENT -->|1 . embed query| EMB[sentence-transformers<br/>all-MiniLM-L6-v2]
    EMB -->|2 . similarity search| VEC[(Supabase pgvector<br/>documents)]
    VEC -->|retrieved context| AGENT

    AGENT -->|3 . prompt + context + tools| CLAUDE{{Claude Haiku 4.5}}
    CLAUDE -->|tool_use| TOOLS[tools.py<br/>get_weather · calculate]
    TOOLS -->|tool_result| CLAUDE
    CLAUDE -->|final answer| AGENT

    AGENT -->|4 . persist turn| MEM
    AGENT -->|answer| API
    API --> Client

    EVAL[evaluator.py<br/>7 graded cases] -.->|calls run_agent directly| AGENT

    style CLAUDE fill:#D4A27F,color:#000
    style VEC fill:#3ECF8E,color:#000
    style MEM fill:#3ECF8E,color:#000
    style EVAL fill:#4A90D9,color:#fff
```

The agent decides on its own whether a tool is needed. `get_weather` and
`calculate` are exposed as tool definitions; nothing in the code inspects the
user's message to route it.

## Run it

**Prerequisites:** Python 3.11, an Anthropic API key, and a Supabase project with
pgvector enabled.

```bash
git clone https://github.com/sadvi11/smart-ai-agent.git
cd smart-ai-agent

python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # installs torch via sentence-transformers; takes a few minutes

cp .env.example .env                 # then fill in the three values below
```

`.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

```bash
python app.py                        # http://localhost:5000
```

> The Supabase client is created at import time and validates its key, so the app
> will not start without those variables set.

**Run the agent directly, without the API:**

```bash
python agent.py
```

**Run the evaluation suite:**

```bash
python evaluator.py
```

## Sample output

```console
$ curl -s -X POST http://localhost:5000/chat \
    -H 'Content-Type: application/json' \
    -d '{"message":"What is the weather in Calgary?","session_id":"demo-1"}' | jq
{
  "answer": "It's currently 3°C and partly cloudy in Calgary.",
  "session_id": "demo-1",
  "turns": 4,
  "status": "success",
  "timestamp": "2026-08-12T14:22:07.481293"
}
```

```console
$ curl -s -X POST http://localhost:5000/history \
    -H 'Content-Type: application/json' \
    -d '{"session_id":"demo-1"}' | jq
{
  "session_id": "demo-1",
  "messages": [
    {"role": "user",      "content": "What is the weather in Calgary?"},
    {"role": "assistant", "content": "It's currently 3°C and partly cloudy in Calgary."}
  ],
  "message_count": 2,
  "status": "success"
}
```

```console
$ curl -s http://localhost:5000/health | jq
{
  "status": "healthy",
  "service": "smart-ai-agent",
  "version": "1.0.0",
  "metrics": { "total_requests": 12, "successful_requests": 11, "failed_requests": 1, "avg_latency_ms": 842 }
}
```

## Evaluation — including the adversarial cases

`evaluator.py` runs 7 graded cases against the live agent. Three are functional
(tool use, memory recall, arithmetic); two are attacks; two are malformed input.

| Case | What it checks |
|---|---|
| Normal weather question | Agent selects `get_weather` unprompted |
| Memory test | Recalls a fact from an earlier turn in the session |
| Math calculation | Selects `calculate` rather than doing mental arithmetic |
| **Prompt injection attack** | Refuses instructions embedded in user input |
| **SQL injection attempt** | Input reaches the vector store without being executed |
| Empty input | Fails gracefully instead of calling the model |
| Nonsense input | Does not hallucinate a confident answer |

![Evaluation summary](screenshots/evaluator-summary.png)
![Evaluation detail](screenshots/evaluator-1.png)

## It works — here it is working

| Tool use and RAG | Retrieved context |
|---|---|
| ![Agent tool use](screenshots/agent-rag-tool-use.png) | ![RAG answers](screenshots/agent-rag-answers.png) |

| Memory across sessions | Health endpoint |
|---|---|
| ![Memory](screenshots/memory-persistence.png) | ![Health](screenshots/health-endpoint-rag-enabled.png) |

| Document store | Supabase rows |
|---|---|
| ![Document store](screenshots/rag-document-store.png) | ![Supabase](screenshots/supabase-documents.png) |

## Project structure

```
.
├── app.py            # Flask API — /chat, /history, /health, /metrics
├── agent.py          # agent loop: retrieve → prompt → tool use → answer
├── rag.py            # embedding + pgvector similarity search
├── memory.py         # conversation persistence (Supabase)
├── tools.py          # tool definitions: get_weather, calculate
├── evaluator.py      # 7-case graded suite, functional + adversarial
├── screenshots/      # evidence for the claims above
├── PRODUCTION.md     # what would need to change to run this for real
└── WHY.md            # why this project exists
```

## Known limitations

Stated plainly, because a README that claims everything works is not credible:

- **Tools are demonstrations.** `get_weather` and `calculate` exist to prove the
  model selects tools correctly. Swapping in real integrations does not change the
  agent loop.
- **Single-process memory metrics.** The counters on `/health` reset on restart;
  real deployment would export to Prometheus.
- **No auth on the API.** Every endpoint is open. See `PRODUCTION.md`.
- **Supabase is required to start.** The client is constructed at import time, so
  there is no offline mode.

## Author

Sadhvi Sharma · Cloud & AI Engineer · Calgary, Alberta
[github.com/sadvi11](https://github.com/sadvi11)
