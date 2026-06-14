# Security And Permissions

This MVP demonstrates permission-aware retrieval and generation using synthetic users and department-level access rules. It is not production authentication, but it exercises the core safety boundary needed by enterprise assistants: restricted context must not reach users or prompts that are not allowed to see it.

## Synthetic Users

The demo includes users such as:

- `finance_user`
- `hr_user`
- `engineer_user`
- `legal_user`
- `admin_user`
- `intern_user`

Each user has a role, department, allowed departments, and access levels.

## Access Levels

Sample documents are tagged with department access levels such as `finance`, `hr`, `engineering`, and `legal`. Department users can access documents for their department plus public/general levels. `admin_user` can access all departments. `intern_user` is limited to public/general access.

## Authentication Simulation

Authentication simulation:

- `ECE_AUTH_MODE=off` for local demos.
- `ECE_AUTH_MODE=api_key` for API-key identity simulation.
- `Authorization: Bearer <token>` and `X-API-Key: <token>` are supported in API-key mode.
- The authenticated user identity is passed into access control.
- Request `user_id` spoofing is rejected when auth is enabled.

This is not production OAuth/OIDC. It is an interview/demo-ready simulation of request identity and RBAC enforcement without external auth services.

## Safe Abstention

When retrieval finds only inaccessible evidence, the system returns:

```text
I could not find accessible documents that support an answer to this question.
```

This avoids implying the existence or content of a restricted document.

## No Restricted Title Or Snippet Leakage

Unauthorized API responses and query logs avoid raw context, raw chunks, source snippets, restricted titles, chunk IDs, and document bodies. Debug fields expose aggregate routing information such as retrieval mode, intent, counts, and latency-oriented metadata.

Query logs intentionally avoid storing raw context chunks or restricted retrieved text. Logs store aggregate metadata such as retrieval mode, intent, citation count, latency, and safe-abstain status. This applies to both in-memory logs and optional SQLite-backed logs.

## Access Control Before Context And Generation

The safety boundary is enforced before context construction and answer generation:

```text
retrieval candidates
  -> access-control filter
  -> reranker
  -> context builder
  -> prompt
  -> answer
```

If a user has no accessible chunks, the context builder returns empty context and the answer generator does not call the LLM client.

## Limitations

- This is not production authentication.
- There is no real identity provider yet.
- There is no organization-level RBAC or tenant isolation yet.
- Demo API keys are local simulation secrets only and must not be used in production.
- Optional SQLite persistence is a local demo store, not a hardened audit system.
- The demo uses synthetic documents and users.

Future work should add real authentication, organization-aware authorization, persistent audit logging, secrets management, and security review for any real enterprise data source.
