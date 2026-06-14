# Evaluation

The Enterprise Context Engine includes deterministic evaluation for the secure answer-generation pipeline. The MVP does not use LLM-as-judge because the first evaluation layer should be transparent, reproducible, fast, and safe to run without external services.

## Metrics

| Metric | Purpose |
| --- | --- |
| Recall@5 | Checks whether expected source documents appear in the top retrieved/cited evidence. |
| MRR | Rewards placing the first relevant source earlier in the ranked evidence. |
| nDCG@5 | Measures ranked source quality with binary relevance. |
| Citation presence | Ensures answered queries include citation markers and metadata, while abstentions do not. |
| Abstention accuracy | Checks whether the system abstains when access or evidence requires it. |
| Restricted leak rate | Detects forbidden restricted titles or terms in unauthorized output/debug. |
| Retrieval mode accuracy | Checks whether routing chose the expected retrieval mode or an acceptable hybrid fallback. |
| Average latency | Tracks end-to-end query time for the evaluated examples. |

## Latest Known Local Metrics

```text
Total examples: 37
Pass rate: 1.00
Mean Recall@5: 0.88
Mean MRR: 0.97
Mean nDCG@5: 0.90
Citation presence: 1.00
Abstention accuracy: 1.00
Restricted leak rate: 0.00
Retrieval mode accuracy: 1.00
```

## Final Portfolio Metrics

```text
sample_docs: 37/37
gitlab_handbook: 18/18
restricted leak rate: 0.00
tests: 233 passed, 1 skipped
```

## Why No LLM-as-Judge Yet

LLM-as-judge can be useful later for answer helpfulness, nuance, and synthesis quality. It is intentionally not part of the MVP evaluator because it adds cost, model variance, provider dependencies, and security review overhead. The current evaluator focuses on deterministic checks that are easier to trust during system development:

- Was the expected evidence surfaced?
- Was the expected retrieval mode selected?
- Did unauthorized users safely abstain?
- Were citations present only when appropriate?
- Did outputs avoid restricted terms?
- Was latency measurable?

## How To Run

```bash
python scripts/run_eval.py
```

The API also exposes evaluation through:

```text
POST /evaluate?source=sample_docs
POST /evaluate?source=gitlab_handbook
POST /evaluate?source=combined
GET /metrics
```

## Source-Specific Evaluation

The project has two deterministic eval sets:

- `sample_docs`: synthetic enterprise policies, including access-control and safe-abstention checks.
- `gitlab_handbook`: local public GitLab Handbook-style fixture docs, focused on public-source retrieval and citation behavior.

`combined` evaluation runs both sets over the combined corpus and should be treated as experimental. Public handbook-style docs can satisfy some queries that are intentionally unauthorized in the synthetic enterprise eval set.

## No-Evidence Abstention

The GitLab real-source evaluation includes impossible/out-of-corpus questions. The evidence gate measures lexical and citation support before generation and abstains when context is too weak.

This keeps the evaluator deterministic while improving hallucination resistance. The gate does not use LLM-as-judge and does not require network access or API keys.

## GitLab Handbook-style Eval

Run:

```bash
python scripts/run_eval.py --source gitlab_handbook
python scripts/run_gitlab_eval.py
```

Latest known local metrics:

```text
Total examples: 18
Pass rate: 1.00
Mean Recall@5: 0.97
Mean MRR: 0.94
Mean nDCG@5: 0.93
Citation presence: 1.00
Abstention accuracy: 1.00
Restricted leak rate: 0.00
Retrieval mode accuracy: 1.00
```

The intentionally impossible/out-of-corpus examples should now safe-abstain before answer generation.
