# Interview Guide

## 30-Second Pitch

I built an enterprise context engine for LLM applications. Instead of naive vector RAG, it uses query analysis, retrieval routing, BM25 and dense hybrid retrieval, progressive disclosure, permission-aware access control, evidence gating, grounded citations, and deterministic evaluation.

## 2-Minute Architecture Explanation

A user query enters through FastAPI or the dashboard. Optional auth resolves the effective demo user. The query analyzer classifies intent and retrieval needs, then the retrieval router chooses BM25, dense, hybrid, metadata lookup, or section lookup. Progressive disclosure first finds candidate documents and sections, then focused chunks. Access control filters evidence before context construction. A reranker orders accessible evidence, the context builder adds citations, the evidence gate checks whether context actually supports the question, and the answer generator returns a grounded answer or safe abstention. Evaluation measures retrieval quality, citation behavior, abstention accuracy, and restricted leak rate.

## Deep-Dive Topics

### Why not naive RAG?

Naive RAG often retrieves nearest chunks and sends them directly to a model. Enterprise systems need permissions, exact policy matching, metadata, explainable routing, citation traceability, and abstention when evidence is weak.

### Why BM25 and dense retrieval?

BM25 is strong for exact terms, policy names, acronyms, section titles, and limits. Dense retrieval helps paraphrases and semantic matches. Hybrid retrieval combines both.

### Why progressive disclosure?

Progressive disclosure reduces context pollution. It first identifies relevant documents and sections, then narrows to chunks that are easier to inspect, filter, rerank, and cite.

### How access control prevents leakage?

Access control runs before context building and answer generation. Inaccessible chunks are filtered out, and unauthorized responses avoid restricted titles, snippets, chunk IDs, and raw context.

### How evidence gate reduces hallucination?

The evidence gate checks lexical overlap, citation presence, metadata/title signals, and retrieval score signals before calling the LLM. If accessible evidence is weak or unrelated, it safe-abstains.

### How evaluation works?

The evaluator uses deterministic examples for synthetic enterprise docs and GitLab Handbook-style fixtures. It checks document/department hits, recall, MRR, nDCG, citations, abstention accuracy, grounded-answer heuristic, retrieval mode accuracy, and restricted leak rate.

### What would change in production?

Production would add OAuth/OIDC, tenant-aware RBAC, PostgreSQL, object storage, background ingestion jobs, observability, managed vector storage, real LLMs, and stronger human evaluation.

## Common Interview Questions

### 1. Why not just upload docs to an LLM?

Because enterprise assistants need permissions, traceability, freshness, evaluation, and abstention. Uploading docs does not enforce per-user access boundaries or provide deterministic quality signals.

### 2. Why use BM25 if you have embeddings?

Enterprise queries often contain exact policy names, acronyms, and compliance language. BM25 handles those exact lexical signals better than embeddings alone.

### 3. How do you prevent unauthorized data leakage?

The pipeline filters by access level before context construction. Unauthorized evidence is not placed into prompts, returned through the API, or stored in logs.

### 4. What is progressive disclosure?

It is a staged retrieval process: discover documents, discover sections, then fetch focused chunks. It makes retrieval more inspectable and reduces irrelevant prompt content.

### 5. How do you evaluate RAG/context systems?

Use deterministic retrieval and safety metrics first: source hit rate, citation presence, abstention accuracy, leak detection, grounded-answer heuristics, and latency. LLM-as-judge can be a later secondary layer.

### 6. What are the limitations?

The default LLM is mocked, demo auth is not real OAuth, GitLab fixtures are synthetic, and production ingestion/observability are not implemented yet.

### 7. How would you scale this?

Move metadata/logs to PostgreSQL, objects to object storage, retrieval vectors to Qdrant or another managed vector store, and ingestion to background workers with observability.

### 8. How would you deploy this?

Package the API and dashboard separately, configure environment-specific storage/vector backends, add secrets management, use CI gates, and deploy behind managed auth and monitoring.

### 9. How would you add real OAuth?

Use OIDC middleware, validate JWTs, map claims to tenant/user/role/department permissions, and keep the access-control interface independent from the identity provider.

### 10. How would you improve retrieval quality?

Add better rerankers, query decomposition, multi-hop retrieval, feedback loops, larger real-source eval sets, and optional LLM-as-judge for answer quality.
