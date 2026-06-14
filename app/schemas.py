"""Shared data shapes for the Enterprise Context Engine MVP."""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    role: str
    department: str
    allowed_departments: tuple[str, ...]
    access_levels: tuple[str, ...]


@dataclass(frozen=True)
class DocumentMetadata:
    title: str
    department: str
    access_level: str
    version: str
    effective_date: str
    document_type: str | None


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    department: str
    access_level: str
    version: str
    effective_date: str
    document_type: str | None
    source_path: str
    body: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    document_title: str
    department: str
    access_level: str
    document_type: str | None
    version: str
    effective_date: str
    section_title: str
    text: str
    word_count: int
    source_path: str


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    document_id: str
    document_title: str
    department: str
    access_level: str
    section_title: str
    text: str
    score: float
    retrieval_method: str
    metadata: dict[str, Any]
    normalized_score: float | None = None


@dataclass(frozen=True)
class RerankedResult:
    chunk_id: str
    document_id: str
    document_title: str
    department: str
    access_level: str
    section_title: str
    text: str
    original_score: float
    rerank_score: float
    final_score: float
    retrieval_method: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Citation:
    source_id: int
    chunk_id: str
    document_id: str
    document_title: str
    department: str
    section_title: str
    access_level: str
    version: str | None = None
    effective_date: str | None = None
    retrieval_method: str | None = None
    score: float | None = None


@dataclass(frozen=True)
class ContextBuildResult:
    query: str
    context_text: str
    citations: list[Citation]
    included_chunks: list[RerankedResult]
    safe_abstain: bool
    safe_message: str | None = None
    debug: dict[str, Any] = field(default_factory=dict)


class EvidenceGateDecision(BaseModel):
    is_supported: bool
    confidence_score: float
    reason: str
    matched_terms: list[str] = Field(default_factory=list)
    missing_terms: list[str] = Field(default_factory=list)
    debug: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class PromptBuildResult:
    query: str
    system_prompt: str
    user_prompt: str
    context_text: str
    citation_count: int
    safe_abstain: bool
    safe_message: str | None = None
    debug: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GeneratedAnswer:
    query: str
    answer: str
    citations: list[Citation]
    safe_abstain: bool
    safe_message: str | None
    model_name: str
    usage: dict[str, Any] = field(default_factory=dict)
    debug: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QueryAnalysis:
    query: str
    intent: str
    department_hint: str | None
    needs_exact_terms: bool
    needs_semantic_search: bool
    needs_metadata_filter: bool
    needs_section_lookup: bool
    needs_comparison: bool
    needs_step_by_step_answer: bool
    detected_terms: list[str]
    confidence: float


@dataclass(frozen=True)
class RetrievalPlan:
    query: str
    retrieval_mode: str
    reason: str
    analysis: QueryAnalysis
    candidate_k: int
    top_k: int
    filters: dict[str, Any]


@dataclass(frozen=True)
class CandidateDocument:
    document_id: str
    document_title: str
    department: str
    access_level: str
    score: float
    matched_sections: list[str] = field(default_factory=list)
    retrieval_methods: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateSection:
    document_id: str
    document_title: str
    section_title: str
    department: str
    access_level: str
    score: float
    retrieval_methods: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProgressiveDisclosureResult:
    query: str
    retrieval_plan: RetrievalPlan
    candidate_documents: list[CandidateDocument]
    candidate_sections: list[CandidateSection]
    focused_chunks: list[RetrievalResult]
    debug: dict[str, Any]


@dataclass(frozen=True)
class AccessDecision:
    user_id: str
    allowed: bool
    reason: str
    allowed_access_levels: list[str]


@dataclass(frozen=True)
class AccessFilterResult:
    user_id: str
    accessible_candidate_documents: list[CandidateDocument]
    accessible_candidate_sections: list[CandidateSection]
    accessible_focused_chunks: list[RetrievalResult]
    filtered_document_count: int
    filtered_section_count: int
    filtered_chunk_count: int
    safe_abstain: bool
    safe_message: str | None = None
    debug: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SecureProgressiveDisclosureResult:
    query: str
    user_id: str
    base_result: ProgressiveDisclosureResult | None
    access_filter_result: AccessFilterResult
    focused_chunks: list[RetrievalResult]
    candidate_documents: list[CandidateDocument]
    candidate_sections: list[CandidateSection]
    safe_abstain: bool
    safe_message: str | None
    debug: dict[str, Any]


@dataclass(frozen=True)
class QueryLogEntry:
    user_id: str
    query: str
    retrieval_mode: str
    latency_ms: int
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EvalExample:
    example_id: str
    question: str
    user_id: str
    expected_document_titles: list[str] = field(default_factory=list)
    expected_departments: list[str] = field(default_factory=list)
    expected_retrieval_mode: str | None = None
    expected_access_allowed: bool = True
    answer_should_abstain: bool = False
    expected_terms: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass(frozen=True)
class EvalExampleResult:
    example_id: str
    question: str
    user_id: str
    answer: str
    safe_abstain: bool
    citations: list[Citation]
    retrieved_document_titles: list[str]
    retrieved_departments: list[str]
    retrieval_mode: str | None
    latency_ms: float
    metrics: dict[str, Any]
    passed: bool
    failure_reasons: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalSummary:
    total_examples: int
    passed_examples: int
    failed_examples: int
    metrics: dict[str, Any]
    results: list[EvalExampleResult]


class QueryRequest(BaseModel):
    user_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    query: str
    user_id: str
    answer: str
    safe_abstain: bool
    citations: list[dict[str, Any]]
    debug: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    status: str
    documents_ingested: int
    chunks_created: int
    active_data_source: str | None = None


class DataSourceRequest(BaseModel):
    mode: str = "sample_docs"


class DataSourceResponse(BaseModel):
    status: str
    active_data_source: str
    documents_ingested: int
    chunks_created: int
