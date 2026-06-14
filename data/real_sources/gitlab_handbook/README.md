# GitLab Handbook Source Directory

This directory holds local Markdown files for the GitLab Handbook ingestion MVP.

Run:

```bash
python scripts/create_gitlab_fixture_docs.py
python scripts/ingest_gitlab_handbook.py --local
```

The generated fixture documents are synthetic excerpts inspired by public handbook structure. They are not official GitLab content. Live downloading/crawling is intentionally not required for tests.
