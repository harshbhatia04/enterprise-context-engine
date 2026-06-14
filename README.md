# Enterprise Context Engine

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Tests](https://img.shields.io/badge/tests-233%2B%20passing-brightgreen)
![Storage](https://img.shields.io/badge/storage-memory%20%7C%20sqlite-lightgrey)
![Vector](https://img.shields.io/badge/vector-memory%20%7C%20qdrant-lightgrey)
<!-- Add CI badge after pushing to GitHub -->

**Permission-aware context engineering for enterprise LLM applications.**

Portfolio status: v1.0-ready

Enterprise Context Engine is a portfolio-grade RAG/context-engineering system for enterprise assistants that must retrieve useful evidence without leaking restricted knowledge.

- Query analysis and retrieval routing
- BM25 + dense + hybrid retrieval
- Progressive disclosure and evidence gating
- Auth/RBAC simulation with safe abstention
- Deterministic evaluation over synthetic and public-style corpora

Enterprise Context Engine is a professional RAG-style system that treats retrieval as a context-engineering pipeline. It combines ingestion, chunking, BM25, dense retrieval, hybrid retrieval, query routing, progressive disclosure, access control, reranking, citation-backed context, grounded answer generation, deterministic evaluation, FastAPI, and a Streamlit dashboard.

The project is designed for enterprise assistants where the system must answer from private knowledge without leaking restricted documents or flooding the model with irrelevant context.

## Why This Is Not Naive RAG

Naive RAG often embeds chunks, retrieves top-k vectors, inserts raw chunks into a prompt, and asks a model to answer. That pattern misses important enterprise requirements:

- Exact policy names, acronyms, versions, and limits matter.
- Users have different document permissions.
- Retrieval should be inspectable.
- Context should be compact and source-traceable.
- Unauthorized users should receive safe abstention.
- Quality and safety should be measured, not guessed.

This system analyzes each query, chooses a retrieval strategy, discovers candidate documents and sections, filters inaccessible evidence, reranks accessible chunks, builds minimal citation-backed context, generates an answer, logs safe metadata, and evaluates deterministic metrics.

## Architecture Overview

```text
User query + user_id
  -> query analyzer
  -> retrieval router
  -> BM25 / dense / hybrid / metadata / section lookup
  -> progressive disclosure
  -> access-control filter
  -> reranker
  -> context builder
  -> citation builder
  -> evidence confidence gate
  -> answer generator
  -> evaluation + query logs
  -> FastAPI + Streamlit dashboard
```

More detail:

- [Architecture](docs/ARCHITECTURE.md)
- [Demo script](docs/DEMO_SCRIPT.md)
- [Evaluation](docs/EVALUATION.md)
- [Security](docs/SECURITY.md)
- [Final report](docs/FINAL_REPORT.md)
- [Interview guide](docs/INTERVIEW_GUIDE.md)
- [Resume bullets](docs/RESUME_BULLETS.md)
- [Roadmap](docs/ROADMAP.md)
- [Limitations](docs/LIMITATIONS.md)

## Demo Assets

- [Demo Video Script](docs/DEMO_VIDEO_SCRIPT.md)
- [GitHub Showcase Guide](docs/GITHUB_SHOWCASE.md)
- [Release Notes](docs/RELEASE_NOTES.md)
- [Screenshot Guide](assets/screenshots/README.md)

## Features

- Synthetic enterprise document corpus across HR, Finance, Engineering, and Legal.
- Optional GitLab Handbook-style public documentation ingestion from local Markdown files.
- Metadata-aware Markdown ingestion and chunking.
- BM25-first exact retrieval.
- Fake offline dense embeddings for deterministic local demos.
- Optional Qdrant-backed dense retrieval for production-style vector search.
- Hybrid retrieval with normalized score fusion.
- Query analyzer and retrieval router.
- Progressive disclosure from documents to sections to focused chunks.
- Department and access-level filtering before generation.
- Reranked, deduplicated, citation-backed context.
- Mock LLM client that requires no API key.
- Optional OpenAI-compatible client path for future use.
- Deterministic evaluation with 37 examples.
- FastAPI backend for query, logs, documents, users, health, and evaluation.
- Streamlit dashboard for demos.
- API and dashboard data-source selection for sample docs, GitLab Handbook-style docs, or a combined corpus.
- Optional SQLite persistence for document metadata, chunks, query logs, and eval summaries.
- Docker and Docker Compose setup for API plus dashboard.

## Tech Stack

- Python 3.11+
- FastAPI
- Streamlit
- Pydantic
- Pytest
- rank-bm25
- NumPy / scikit-learn
- Sentence Transformers dependency available for future real embeddings
- Optional qdrant-client for Qdrant vector storage
- SQLite via Python standard library
- Docker Compose

No LangChain is used in the MVP.

## Quickstart Local

Create sample documents:

```bash
python scripts/create_sample_docs.py
```

Inspect ingestion:

```bash
python scripts/ingest_sample_docs.py
```

Run tests:

```bash
python -m pytest
```

Run evaluation:

```bash
python scripts/run_eval.py
python scripts/run_eval.py --source sample_docs
python scripts/run_eval.py --source gitlab_handbook
python scripts/run_gitlab_eval.py
```

Generate and ingest local GitLab Handbook-style fixtures:

```bash
python scripts/create_gitlab_fixture_docs.py
python scripts/ingest_gitlab_handbook.py --local
```

The current GitLab Handbook MVP uses local Markdown files. Live crawling/downloading is intentionally not required for tests.

Start the API:

```bash
make api
```

Start the dashboard:

```bash
make dashboard
```

Open:

```text
API: http://localhost:8000
Dashboard: http://localhost:8501
```

## Dashboard UI

The project includes a polished Streamlit dashboard for demos, screenshots, and local walkthroughs. In the default
local mode, auth is off and no API key is required. The API key input appears only when `ECE_AUTH_MODE=api_key`.

The dashboard connects to the local FastAPI backend. No external API is required for the default demo.

## Quickstart Docker

Copy environment defaults:

```bash
copy .env.example .env
```

Build containers:

```bash
make docker-build
```

Run API and dashboard:

```bash
make docker-up
```

Stop containers:

```bash
make docker-down
```

Docker runs:

- API on `http://localhost:8000`
- Dashboard on `http://localhost:8501`

The compose setup defaults the API to in-memory retrieval. An optional Qdrant service is included for vector-store experiments and can be started with `docker compose up qdrant`.

## Demo Workflow

1. Start API.
2. Start dashboard.
3. Ingest sample docs from the Health page.
4. Ask as `finance_user`: `What is the invoice approval limit?`
5. Ask as `intern_user`: `What is the invoice approval limit?`
6. Show safe abstention with no restricted title leak.
7. Ask as `engineer_user`: `How do we restore production after a bad release?`
8. Ask as `admin_user`: `NDA policy`
9. Run evaluation.
10. Show metrics and query logs.

Optional real-data ingestion demo:

```bash
python scripts/create_gitlab_fixture_docs.py
python scripts/ingest_gitlab_handbook.py --local
```

This prints loaded GitLab Handbook-style documents, chunks, department distribution, and example chunks. Fixture text is synthetic and not official GitLab content.

Optional dashboard data-source demo:

```bash
python scripts/create_gitlab_fixture_docs.py
make api
make dashboard
```

On the Health page, load `gitlab_handbook`, ask as `intern_user`: `What does the handbook say about remote work?`, then switch back to `sample_docs` for the enterprise permission demo.

## Milestone 13: Real Public Data Ingestion - GitLab Handbook MVP

The project now supports optional ingestion of GitLab Handbook-style public enterprise documentation. Fake company documents remain as deterministic test fixtures, while real/public-source ingestion improves demo credibility.

The MVP supports local GitLab Handbook-style Markdown files under `data/real_sources/gitlab_handbook/`. Live crawling/downloading is intentionally not required for tests.

## Milestone 14: Data Source Selection

The API and dashboard now support switching between synthetic enterprise docs, GitLab Handbook-style public docs, and a combined corpus.

Available modes:

- `sample_docs`
- `gitlab_handbook`
- `combined`

Load GitLab Handbook-style docs through the API:

```bash
curl -X POST http://localhost:8000/ingest/data-source \
  -H "Content-Type: application/json" \
  -d "{\"mode\":\"gitlab_handbook\"}"
```

List available sources:

```bash
curl http://localhost:8000/data-sources
```

The original deterministic enterprise evaluation set still targets `sample_docs`; GitLab Handbook-style docs now have their own separate deterministic eval set.

## Milestone 15: Real-Source Evaluation

The project now includes a separate deterministic evaluation set for the GitLab Handbook-style corpus. This allows the public-source ingestion path to be measured independently from the synthetic enterprise-doc evaluation set.

Run source-specific evals:

```bash
python scripts/run_eval.py --source sample_docs
python scripts/run_eval.py --source gitlab_handbook
python scripts/run_gitlab_eval.py
```

API examples:

```bash
curl -X POST "http://localhost:8000/evaluate?source=sample_docs"
curl -X POST "http://localhost:8000/evaluate?source=gitlab_handbook"
```

`combined` evaluation is available as an experimental smoke test because public GitLab-style docs can change the behavior of sample-doc access-control examples.

## Milestone 16: Evidence Confidence Gate

The system now includes a deterministic evidence gate before answer generation. It checks whether the retrieved accessible context actually supports the user's question using lexical overlap, citation presence, title/section metadata, and retrieval score signals.

If evidence is weak or unrelated, the system safe-abstains before calling the LLM:

```text
I could not find accessible documents that support an answer to this question.
```

This improves reliability for out-of-corpus questions and reduces hallucination risk without using LLM-as-judge.

## Milestone 17: Optional Qdrant Vector Store

The project now includes optional Qdrant-backed dense retrieval. In-memory dense retrieval remains the default for offline tests and demos, while Qdrant provides a production-style vector database option for larger corpora and persistent semantic search.

Qdrant is optional. The system works without it.

Run the embedded in-memory Qdrant demo:

```bash
python scripts/test_qdrant_retrieval.py
```

Start a local Qdrant service for experiments:

```bash
docker compose up qdrant
```

Vector backend configuration defaults to memory:

```text
ECE_VECTOR_BACKEND=memory
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=enterprise_context_chunks
```

## Milestone 18: Optional SQLite Persistence

The project now supports optional SQLite persistence for document metadata, chunks, query logs, and evaluation summaries. In-memory storage remains the default for fast tests and demos.

SQLite persistence is optional. It is intended to demonstrate production-style state retention without requiring PostgreSQL or external infrastructure.

Run the SQLite persistence smoke test:

```bash
python scripts/test_sqlite_persistence.py
```

Environment settings:

```text
ECE_STORAGE_BACKEND=sqlite
ECE_SQLITE_PATH=data/state/enterprise_context_engine.db
```

PowerShell API example:

```powershell
$env:ECE_STORAGE_BACKEND="sqlite"
$env:ECE_SQLITE_PATH="data/state/enterprise_context_engine.db"
uvicorn app.main:app --reload
```

## Milestone 20: Production-Style Auth/RBAC Simulation

The API now supports optional API-key based authentication for local enterprise demos. When enabled, the authenticated identity is used for permission-aware retrieval and `user_id` spoofing is rejected.

Auth is off by default, so local dashboard and curl demos continue to work:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"finance_user\",\"query\":\"What is the invoice approval limit?\"}"
```

Enable API-key mode:

```bash
ECE_AUTH_MODE=api_key uvicorn app.main:app --reload
```

PowerShell:

```powershell
$env:ECE_AUTH_MODE="api_key"
uvicorn app.main:app --reload
```

Authenticated request:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-finance-key" \
  -d "{\"user_id\":\"finance_user\",\"query\":\"What is the invoice approval limit?\"}"
```

Demo API keys are for local simulation only. Do not use them in production.

## Evaluation Metrics

| Metric | Latest local value |
| --- | ---: |
| Total examples | 37 |
| Pass rate | 1.00 |
| Mean Recall@5 | 0.88 |
| Mean MRR | 0.97 |
| Mean nDCG@5 | 0.90 |
| Citation presence | 1.00 |
| Abstention accuracy | 1.00 |
| Restricted leak rate | 0.00 |
| Retrieval mode accuracy | 1.00 |

The evaluator is deterministic and does not use LLM-as-judge in the MVP.

## Security And Access Control

The demo uses synthetic users and department-based access levels. Access control happens before context building and answer generation. If a user has no accessible evidence, the system returns a safe abstention response and does not call the LLM client.

Unauthorized responses and logs avoid raw context, raw chunks, restricted snippets, and restricted document titles. See [Security](docs/SECURITY.md).

## API Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Root status |
| POST | `/ingest/sample` | Ingest bundled sample documents |
| GET | `/data-sources` | List selectable corpus modes |
| POST | `/ingest/data-source` | Load `sample_docs`, `gitlab_handbook`, or `combined` |
| POST | `/query` | Ask a question as a user |
| GET | `/logs` | View recent sanitized query logs |
| GET | `/users` | View demo users |
| GET | `/documents` | View document metadata only |
| GET | `/health` | View API health and ingestion counts |
| POST | `/evaluate` | Run deterministic evaluation |
| GET | `/metrics` | View latest evaluation metrics |

## Dashboard Pages

- Ask Assistant
- Documents
- Evaluation
- Query Logs
- Health

The dashboard uses `ECE_API_URL`, defaulting to `http://localhost:8000`.

## Useful Commands

```bash
make sample-docs
make ingest
make bm25-demo
make hybrid-demo
make routing-demo
make progressive-demo
make access-demo
make context-demo
make answer-demo
make auth-demo
make qdrant-demo
make qdrant-up
make sqlite-demo
make gitlab-fixtures
make gitlab-ingest
make real-data-demo
make eval
make gitlab-eval
make check
make lint
make ci
make test
make smoke
```

## Interview Pitch

I built an enterprise context engine for LLM applications. Instead of naive vector RAG, it uses query analysis, retrieval routing, BM25 and dense hybrid retrieval, progressive disclosure, metadata-aware access control, reranking, grounded citations, and deterministic evaluation. The system minimizes context pollution while preserving answer quality, source traceability, and permission safety.

## Roadmap

- Additional public-data ingestion: SEC filings, Kubernetes docs, NIST AI RMF
- Persistent PostgreSQL metadata/log store
- Real authentication and organization-level RBAC
- LLM-as-judge evaluation as optional secondary eval
- Deployment to cloud
