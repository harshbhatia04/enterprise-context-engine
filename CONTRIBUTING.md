# Contributing

Thanks for helping improve Enterprise Context Engine. The project is designed to stay deterministic, local-first, and safe to run without API keys.

## Local Setup

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
python scripts/create_sample_docs.py
```

## Quality Checks

Run the lightweight project check:

```bash
python scripts/check_project.py
```

Run lint checks used by CI:

```bash
python -m ruff check app scripts tests --select F
```

Run the test suite:

```bash
python -m pytest
```

## Evaluation

Run deterministic evals:

```bash
python scripts/run_eval.py --source sample_docs
python scripts/run_eval.py --source gitlab_handbook
```

These evals do not use LLM-as-judge and do not require external services.

## Auth Simulation

Run auth-specific tests:

```bash
python -m pytest tests/test_auth.py tests/test_api.py
```

Tests must not require real secrets. Use only deterministic demo API keys and keep `ECE_AUTH_MODE=off` as the default local mode.

## API And Dashboard

Start the API:

```bash
uvicorn app.main:app --reload
```

Start the dashboard:

```bash
streamlit run dashboard/streamlit_app.py
```

## Storage Backends

The default storage backend is memory:

```text
ECE_STORAGE_BACKEND=memory
```

Optional SQLite persistence can be enabled locally:

```text
ECE_STORAGE_BACKEND=sqlite
ECE_SQLITE_PATH=data/state/enterprise_context_engine.db
```

SQLite is optional and should not be required for ordinary tests.

## Vector Backends

The default vector backend is memory:

```text
ECE_VECTOR_BACKEND=memory
```

Qdrant support is optional and guarded. Do not require a Qdrant server for tests or CI.

## Project Rules

- Do not require API keys for tests.
- Tests must not require real secrets.
- Keep fake docs deterministic.
- Do not store raw context, raw chunks, or restricted retrieved text in query logs.
- Keep Qdrant and SQLite optional.
- Avoid adding heavyweight tooling unless it clearly improves reliability.
