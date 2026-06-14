# Demo Video Script

## 0:00-0:30 - Problem

Most RAG demos retrieve chunks blindly. Enterprise LLM systems need permission-aware context, citation grounding, no-evidence abstention, evaluation, and auditability.

Enterprise Context Engine demonstrates how those pieces fit together in a local, inspectable project.

For this local demo, auth is off, so no API key is required. The dashboard connects to the local FastAPI backend
running at `127.0.0.1:8000`.

## Screenshot-Friendly Demo Sequence

1. Show the dashboard Health page with the local backend online.
2. Show the finance user invoice answer with citations.
3. Show the intern safe abstention for the same finance question.
4. Show the GitLab Handbook-style remote work public answer.
5. Show the evidence gate abstention for an unsupported acquisition-plan question.
6. Show the Evaluation page with deterministic metrics.

## 0:30-1:00 - Architecture

The request enters through FastAPI or the Streamlit dashboard. A query analyzer and retrieval router choose BM25, dense, hybrid, metadata, or section lookup. Progressive disclosure narrows broad results into focused chunks. Access control filters evidence before generation. The evidence gate checks whether accessible context supports the answer. Then the answer generator returns citation-backed output or safe abstention. Deterministic evaluation checks quality and restricted leak behavior.

## 1:00-2:00 - Enterprise Access-Control Demo

1. Load `sample_docs`.
2. Ask as `finance_user`:

```text
What is the invoice approval limit?
```

Expected: answer with citations from finance documents.

3. Ask the same query as `intern_user`.

Expected: safe abstention.

Explain: The system does not merely hide the answer at the UI layer. Restricted context is filtered before answer generation, so the model never receives inaccessible finance evidence.

## 2:00-2:45 - Public Handbook Demo

1. Switch to `gitlab_handbook`.
2. Ask as `intern_user`:

```text
What does the handbook say about remote work?
```

Expected: answer with citations.

Explain: Public-source docs remain accessible even to low-privilege users.

## 2:45-3:30 - No-Evidence Abstention

Ask:

```text
What is the unreleased acquisition plan?
```

Expected: safe abstention.

Explain: The evidence gate checks whether accessible context actually supports the question. If retrieved context is weak or unrelated, the system abstains before answer generation.

## 3:30-4:15 - Evaluation And Quality

Show:

```text
sample_docs: 37/37
gitlab_handbook: 18/18
restricted leak rate: 0.00
tests: 233 passed, 1 skipped
```

Mention CI/CD, deterministic eval, ruff checks, import smoke tests, and release-check commands.

## 4:15-5:00 - Production Readiness And Limitations

Mention optional SQLite persistence, optional Qdrant vector store, API-key auth simulation, Docker support, and CI quality gates.

Be clear about limitations: this is not real OAuth/OIDC, and the GitLab-style fixture text is synthetic handbook-style content, not official GitLab content.

Close with:

```text
This project demonstrates permission-aware context engineering for enterprise LLM applications.
```
