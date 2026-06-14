# Demo Script

Use this script for a local portfolio walkthrough or interview demo.

## 5-Minute Demo Flow

1. Show the README architecture summary and badges.
2. Start the API and dashboard with `make api` and `make dashboard`.
3. Load `sample_docs` from the Health page.
4. Ask as `finance_user`: `What is the invoice approval limit?`
5. Ask as `intern_user`: `What is the invoice approval limit?`
   - Expected: safe abstention with no finance title leakage.
6. Switch to `gitlab_handbook`.
7. Ask as `intern_user`: `What does the handbook say about remote work?`
   - Expected: public handbook-style answer with citations.
8. Run evaluation for `sample_docs` and `gitlab_handbook`.
9. Show CI/tests: `python -m pytest`, ruff check, and eval smoke tests.

## Setup

Before demo:

- Run `python -m pytest`
- Run `python scripts/run_eval.py --source sample_docs`
- Run `python scripts/run_eval.py --source gitlab_handbook`

1. Start the API:

```bash
make api
```

2. Start the dashboard:

```bash
make dashboard
```

3. Open the dashboard at `http://localhost:8501`.

4. On the Health page, click `Ingest Sample Docs`.

## Walkthrough

1. Ask as `finance_user`: `What is the invoice approval limit?`
   - Expected: the assistant answers with citations from finance documents.
   - Talking point: the system routes the query, retrieves evidence, builds context, and cites sources.

2. Ask as `intern_user`: `What is the invoice approval limit?`
   - Expected: safe abstention.
   - Talking point: access control happens before generation, so restricted finance context is never exposed to the model.

3. Ask as `engineer_user`: `How do we restore production after a bad release?`
   - Expected: engineering answer with citations.
   - Talking point: hybrid retrieval and progressive disclosure surface production, deployment, rollback, and backup evidence.

4. Ask as `admin_user`: `NDA policy`
   - Expected: legal answer with citations.
   - Talking point: exact terms and policy names are handled well because BM25 is first-class.

5. Open the Evaluation page and click `Run Evaluation`.
   - Expected: pass rate, retrieval metrics, citation behavior, abstention accuracy, restricted leak rate, and latency.
   - Talking point: this is not only a demo app; it has deterministic quality and safety measurement.
   - Use `sample_docs` to demonstrate enterprise access-control evaluation.
   - Use `gitlab_handbook` to demonstrate public-source retrieval evaluation.

6. Open the Query Logs page.
   - Expected: recent queries with user, retrieval mode, intent, safe abstention, citation count, and latency.
   - Talking point: logs intentionally avoid raw context and restricted snippets.

## Optional Real-Data Ingestion Demo

1. Generate GitLab fixtures:

```bash
python scripts/create_gitlab_fixture_docs.py
```

2. Load `gitlab_handbook` from the dashboard Health page.

3. Ask as `intern_user`: `What does the handbook say about remote work?`
   - Expected: answer with public GitLab Handbook-style citations.
   - Talking point: GitLab fixture docs are public, so even `intern_user` can access them.

4. Show public citations and the active data source in debug.

5. Switch back to `sample_docs`.

6. Show the enterprise access-control demo again:
   - `finance_user`: `What is the invoice approval limit?`
   - `intern_user`: `What is the invoice approval limit?`
   - Expected: finance user receives citations; intern user safe-abstains.

## Optional CLI Real-Data Demo

```bash
python scripts/create_gitlab_fixture_docs.py
python scripts/ingest_gitlab_handbook.py --local
```

Show the output:
   - document count
   - chunk count
   - department distribution
   - first few titles
   - example chunks

Talking point: fake company docs remain the deterministic test fixture, while GitLab Handbook-style Markdown ingestion demonstrates how public enterprise documentation can enter the same `Document` and `Chunk` pipeline.

## Interview Talking Points

- This is context engineering, not a simple vector-search wrapper.
- Retrieval strategy is selected per query.
- BM25 remains important for enterprise exact terms.
- Progressive disclosure reduces prompt pollution.
- Access control happens before context building and generation.
- Answers are grounded with citations.
- Evaluation is deterministic in the MVP, so quality and safety are reproducible.
- The API and dashboard make the project easy to demo, test, and extend.
