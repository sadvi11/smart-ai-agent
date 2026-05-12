# Autonomous Smart AI Agent v2.0

> Production-grade AI agent with RAG pipeline, tool use, persistent memory, and automated security evaluation.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)
[![Claude API](https://img.shields.io/badge/Claude_API-Anthropic-D4A27F)](https://anthropic.com)
[![Flask](https://img.shields.io/badge/Flask-REST_API-000000?logo=flask)](https://flask.palletsprojects.com)
[![Supabase](https://img.shields.io/badge/Supabase-pgvector-3ECF8E?logo=supabase)](https://supabase.com)
[![RAG](https://img.shields.io/badge/RAG-pgvector%20%2B%20Semantic%20Search-blue)]()
[![Status](https://img.shields.io/badge/Status-Deployed%20%26%20Verified-2ea44f)]()

---

## What This Project Does

An autonomous AI agent with a full RAG (Retrieval Augmented Generation) pipeline —
the agent independently decides which tool to invoke, retrieves relevant context from
an uploaded knowledge base using semantic search, and maintains persistent memory
across sessions. Includes a 7-test automated evaluation framework covering functional
behaviour and security robustness — achieving 86% pass rate including prompt injection
and SQL injection attack scenarios.

---

## Architecture

```
                        USER REQUEST
                             │
                    ┌────────▼────────┐
                    │   Flask API     │
                    │  /chat          │
                    │  /upload        │
                    │  /search        │
                    │  /documents     │
                    │  /history       │
                    │  /health        │
                    └────────┬────────┘
                             │
              ┌──────────────▼──────────────┐
              │         agent.py            │
              │      Decision Layer         │
              │    (AMF equivalent)         │
              │                             │
              │  1. Retrieve RAG context    │
              │  2. Build system prompt     │
              │  3. Call Claude API         │
              │  4. Execute tools if needed │
              └──┬──────────┬──────────┬───┘
                 │          │          │
        ┌────────▼──┐ ┌─────▼──┐ ┌────▼──────────┐
        │  rag.py   │ │tools.py│ │  memory.py    │
        │ RAG Layer │ │Execution│ │  Data Layer   │
        │           │ │ Layer  │ │  (UDM equiv)  │
        │ • Chunk   │ │        │ │  Supabase     │
        │ • Embed   │ │Weather │ │  PostgreSQL   │
        │ • Search  │ │Calc    │ │               │
        └─────┬─────┘ └────────┘ └───────────────┘
              │
        ┌─────▼──────────┐
        │ Supabase       │
        │ pgvector store │
        │ 384-dim vectors│
        └────────────────┘
```

---

## Nokia 5G → AI Agent Architecture Mapping

| Nokia 5G Function | AI Agent Equivalent | Purpose |
|---|---|---|
| AMF (Access & Mobility) | `agent.py` | Decision-making — routes requests to right tool |
| SMF (Session Management) | `tools.py` | Execution — manages tool invocation lifecycle |
| UDM (Unified Data Management) | `memory.py` | Persistent cross-session conversation state |
| OAM Knowledge Base | `rag.py` + pgvector | Document knowledge base with semantic search |
| N6 Interface (external) | Flask REST API | Exposes agent to external consumers |
| NF Access Control | `.env` secrets | Zero hardcoded credentials |

---

## RAG Pipeline

```
DOCUMENT INGESTION              QUERY RETRIEVAL
──────────────────             ─────────────────
POST /upload                   User question
      │                              │
  chunk_text()               embed_text(query)
  (500-char chunks)                  │
      │                    cosine similarity search
  embed_text()              (numpy, Python-side)
  (384-dim vector)                   │
      │                     top-k relevant chunks
  store in Supabase                  │
  (pgvector column)         inject into system prompt
                                     │
                             Claude answers with
                             YOUR knowledge
```

---

## Components

| Component | Technology | Purpose |
|---|---|---|
| LLM Engine | Claude API (claude-haiku) | Autonomous reasoning and tool selection |
| RAG Pipeline | sentence-transformers + pgvector | Document embedding, storage, semantic retrieval |
| Embedding Model | all-MiniLM-L6-v2 (384 dims) | Converts text to semantic vectors locally |
| Vector Store | Supabase pgvector | Stores and searches document embeddings |
| Tool Use | Anthropic Function Calling | Weather API + Calculator integration |
| Memory | Supabase (PostgreSQL) | Persistent conversation history across sessions |
| API Layer | Flask REST | 6 production endpoints |
| Evaluation | Custom Python framework | 7 automated tests including security scenarios |

---

## Evaluation Framework — 86% Pass Rate

| Test | Type | Result |
|---|---|---|
| Basic conversation | Functional | ✅ Pass |
| Weather tool invocation | Tool use | ✅ Pass |
| Calculator tool invocation | Tool use | ✅ Pass |
| Memory persistence across sessions | Memory | ✅ Pass |
| RAG document retrieval | RAG | ✅ Pass |
| Prompt injection attack | Security | ✅ Pass |
| SQL injection attempt | Security | ✅ Pass |

**Overall: 6/7 tests passing = 86% pass rate**

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Chat with RAG-enhanced agent |
| `/upload` | POST | Upload document to knowledge base |
| `/search` | POST | Search knowledge base directly |
| `/documents` | GET | List all documents in knowledge base |
| `/documents/<name>` | DELETE | Remove document from knowledge base |
| `/history/<id>` | GET | Get conversation history |
| `/health` | GET | Service health + RAG status |

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
# Add ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY

# Run
python app.py

# Upload a document to the knowledge base
curl -X POST http://localhost:5001/upload \
  -H "Content-Type: application/json" \
  -d '{"text": "Your document content here", "source": "my-doc"}'

# Chat — agent now uses your document
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What does the document say about X?"}'

# Check health
curl http://localhost:5001/health
```

---

## Security Design

- **Prompt injection hardening** — tested against adversarial inputs
- **SQL injection testing** — Supabase queries validated
- **Secret management** — all credentials in `.env`, never committed
- **DevSecOps evaluation** — automated security test suite in `evaluator.py`

---

## Key Design Decisions

**Why RAG instead of fine-tuning?**
Fine-tuning bakes knowledge into the model permanently — expensive and inflexible.
RAG retrieves knowledge dynamically from an updatable database. Upload a new document
and the agent immediately knows it — no retraining required.

**Why Python-side cosine similarity?**
Computed using numpy directly on fetched embeddings — avoids PostgREST type casting
complexity. For production scale with millions of documents, move to pgvector RPC
with ivfflat index for sub-millisecond retrieval.

**Why all-MiniLM-L6-v2 for embeddings?**
384 dimensions — fast, small, good quality. Runs locally with no API key.
Same model used in many production RAG systems.

**Why tool use AND RAG together?**
Tools answer real-time questions (weather, calculations).
RAG answers questions about YOUR documents.
Together: agent has live data access AND a personal knowledge base.

---

## Repository Structure

```
smart-ai-agent/
├── agent.py        # Core agent — RAG retrieval + Claude API + tool selection
├── rag.py          # RAG pipeline — chunk, embed, store, retrieve
├── tools.py        # Tool implementations — Weather API, Calculator
├── memory.py       # Supabase memory — conversation history
├── evaluator.py    # 7-test automated evaluation framework
├── app.py          # Flask REST API — 6 production endpoints
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Interview Talking Points

- **RAG architecture** — chunking, embedding, vector search, context injection
- **pgvector** — what it is, why Supabase supports it, how cosine similarity works
- **LLM tool use** — how the agent decides which tool to call
- **Evaluation framework** — why you test AI systems, what prompt injection is
- **Edge cases** — what happens when RAG finds no relevant context
- **Production considerations** — scaling vector search, embedding model choice

---

## Author

**Sadhvi Sharma** — Cloud & AI Engineer
Nokia India (5G Packet Core) → Cloud & AI Engineering
Calgary, AB, Canada | Permanent Resident | Open to Relocation

[LinkedIn](https://linkedin.com/in/sadhvi-sharma-5789a6249) | [GitHub](https://github.com/sadvi11)
