"""Optional real/public data ingestion modules."""

from app.ingestion.real_data.gitlab_handbook import (
    infer_gitlab_department,
    ingest_gitlab_handbook_directory,
    load_gitlab_handbook_directory,
    normalize_gitlab_metadata,
)

__all__ = [
    "infer_gitlab_department",
    "ingest_gitlab_handbook_directory",
    "load_gitlab_handbook_directory",
    "normalize_gitlab_metadata",
]
