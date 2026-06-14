.PHONY: sample-docs ingest bm25 bm25-demo hybrid-demo routing-demo progressive-demo access-demo context-demo answer-demo auth-demo qdrant-demo qdrant-up sqlite-demo gitlab-fixtures gitlab-ingest real-data-demo gitlab-eval test check lint ci release-check portfolio-check api dashboard eval eval-all docker-build docker-up docker-down smoke

sample-docs:
	python scripts/create_sample_docs.py

ingest:
	python scripts/ingest_sample_docs.py

bm25:
	python scripts/test_bm25_retrieval.py

bm25-demo:
	python scripts/test_bm25_retrieval.py

hybrid-demo:
	python scripts/test_dense_hybrid_retrieval.py

routing-demo:
	python scripts/test_query_routing.py

progressive-demo:
	python scripts/test_progressive_disclosure.py

access-demo:
	python scripts/test_access_control.py

context-demo:
	python scripts/test_context_building.py

answer-demo:
	python scripts/test_answer_generation.py

auth-demo:
	python -m pytest tests/test_auth.py tests/test_api.py

qdrant-demo:
	python scripts/test_qdrant_retrieval.py

qdrant-up:
	docker compose up qdrant

sqlite-demo:
	python scripts/test_sqlite_persistence.py

gitlab-fixtures:
	python scripts/create_gitlab_fixture_docs.py

gitlab-ingest:
	python scripts/ingest_gitlab_handbook.py --local

real-data-demo:
	python scripts/create_gitlab_fixture_docs.py
	python scripts/ingest_gitlab_handbook.py --local

test:
	python -m pytest

check:
	python scripts/check_project.py

lint:
	python -m ruff check app scripts tests --select F

ci:
	python scripts/check_project.py
	python -m ruff check app scripts tests --select F
	python scripts/create_sample_docs.py
	python scripts/create_gitlab_fixture_docs.py
	python scripts/run_eval.py --source sample_docs
	python scripts/run_eval.py --source gitlab_handbook
	python -m pytest

release-check:
	python scripts/check_project.py
	python -m ruff check app scripts tests --select F
	python scripts/run_eval.py --source sample_docs
	python scripts/run_eval.py --source gitlab_handbook
	python -m pytest

portfolio-check: release-check

api:
	uvicorn app.main:app --reload

dashboard:
	streamlit run dashboard/streamlit_app.py

eval:
	python scripts/run_eval.py

gitlab-eval:
	python scripts/run_gitlab_eval.py

eval-all:
	python scripts/run_eval.py --source sample_docs
	python scripts/run_eval.py --source gitlab_handbook

docker-build:
	docker compose build

docker-up:
	docker compose up

docker-down:
	docker compose down

smoke:
	python scripts/create_sample_docs.py
	python scripts/ingest_sample_docs.py
	python scripts/run_eval.py
	python -m pytest
