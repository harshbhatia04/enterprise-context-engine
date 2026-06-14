# Release Notes

## v1.0.0

### Highlights

- Portfolio-ready Enterprise Context Engine for permission-aware LLM applications.
- Query analysis, retrieval routing, progressive disclosure, access control, evidence gating, and citation-backed answers.
- FastAPI backend, Streamlit dashboard, Docker support, CI quality gates, and final interview/demo documentation.

### Core Features

- Synthetic enterprise corpus across HR, Finance, Engineering, and Legal.
- GitLab Handbook-style public fixture corpus for public-source demos.
- BM25, dense, hybrid, metadata, and section-aware retrieval paths.
- Safe abstention for unauthorized or unsupported questions.
- API-key auth/RBAC simulation for local demos.

### Evaluation Results

- sample_docs eval: 37/37
- gitlab_handbook eval: 18/18
- restricted leak rate: 0.00
- tests: 233 passed, 1 skipped

### Security Behavior

- Access control runs before context construction and answer generation.
- Unauthorized responses avoid restricted titles, snippets, raw chunks, and raw context.
- Query logs are sanitized and avoid raw retrieved context.
- API-key auth simulation rejects `user_id` spoofing when enabled.

### Infrastructure

- FastAPI API and Streamlit dashboard.
- Optional SQLite persistence.
- Optional Qdrant vector store.
- Docker and Docker Compose files.
- GitHub Actions CI with project checks, ruff F-level linting, deterministic evals, and pytest.

### Known Limitations

- Demo auth is not production OAuth/OIDC.
- GitLab-style fixture text is synthetic and not official GitLab content.
- Mock LLM is default; real LLM behavior requires additional validation.
- No background ingestion workers, observability stack, or cloud deployment yet.

### Future Work

- Real public-source crawlers/downloaders.
- OAuth/OIDC and tenant-aware RBAC.
- PostgreSQL, object storage, and background ingestion jobs.
- Stronger reranking, query decomposition, multi-hop retrieval, and optional LLM-as-judge evaluation.
