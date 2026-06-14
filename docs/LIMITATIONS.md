# Limitations

- Demo auth is API-key simulation, not real OAuth/OIDC.
- GitLab fixture text is synthetic handbook-style content, not official text.
- Qdrant is optional and may be skipped without `qdrant-client`.
- Evaluation is deterministic and not a substitute for human review.
- Mock LLM is default; real LLM behavior may differ.
- No background ingestion jobs yet.
- No production secrets management.
- No tenant isolation or organization-level RBAC.
- No cloud deployment in this repository state.
- SQLite persistence is a local demo store, not a hardened audit system.
