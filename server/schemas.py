"""JSON shapes for API endpoints — contracts between client and server."""

from pydantic import BaseModel, Field, model_validator


class IngestRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200_000, example="RAG grounds answers in your own documents.")
    document_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        pattern=r"^[A-Za-z0-9._:/-]+$",
        example="week3-notes.md",
        description="Stable ID for the document. Re-ingesting the same ID replaces its chunks.",
    )
    chunk_size: int = Field(800, ge=100, le=4_000)
    chunk_overlap: int = Field(100, ge=0, le=1_000)

    @model_validator(mode="after")
    def _overlap_smaller_than_chunk(self) -> "IngestRequest":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size.")
        return self


class IngestResponse(BaseModel):
    document_id: str
    chunks_added: int
    chunks_replaced: int
    total_chunks: int
    tokens_used: int
    cost_usd: float


class SearchRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=10_000, description="Natural-language query to embed and match against stored chunks.")
    k: int = Field(3, ge=1, le=20, description="How many top chunks to return.")


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    score: float = Field(..., ge=-1.0, le=1.0, description="Cosine similarity (1.0 = identical).")
    text: str


class SearchResponse(BaseModel):
    results: list[SearchHit]
    tokens_used: int
    cost_usd: float


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, example="What is an API?")


class AskResponse(BaseModel):
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    tokens_used: int
    cost_usd: float
    citations: list[str] = Field(default_factory=list, description="Chunk IDs the answer cited that were actually retrieved.")
    refused: bool = Field(False, description="True when no documents were available or the LLM could not answer from context.")


class EstimateRequest(BaseModel):
    input_tokens: int = Field(..., ge=500, le=500_000)
    result_shape: str = Field(..., min_length=1)
    primary_steps: int = Field(..., ge=1, le=5)
    checker_steps: int = Field(..., ge=0, le=3)
    tasks_per_day: int = Field(..., ge=1, le=10_000)
    workload_note: str | None = None
    reasoning_depth: int | None = Field(None, ge=1, le=5)


class ModelEstimateRow(BaseModel):
    model_id: str
    provider: str
    name: str
    scenario: str
    cost_per_task_usd: float
    monthly_usd: float
    output_tokens: int
    attempted_calls: float
    eligible: bool
    ineligible_reason: str | None = None


class EstimateResponse(BaseModel):
    result_shapes: list[str]
    recommendation: ModelEstimateRow | None
    likely_comparison: list[ModelEstimateRow]
    scenario_ranges: list[ModelEstimateRow]


class ComplexityDimensionsRow(BaseModel):
    label: str
    composite_score: int
    input_size: int
    output_depth: int
    reasoning_depth: int
    verification_need: int
    ambiguity_risk: int
    agentic_pattern: int
    uncertainty_pct: float


class WorkloadDerivedRow(BaseModel):
    input_tokens_raw: int
    input_tokens: int
    result_shape: str
    primary_steps: int
    checker_steps: int
    tasks_per_day: int


class CostRangeRow(BaseModel):
    broad_min_per_task_usd: float
    broad_max_per_task_usd: float
    broad_min_monthly_usd: float
    broad_max_monthly_usd: float
    close_center_per_task_usd: float
    close_low_per_task_usd: float
    close_high_per_task_usd: float
    close_delta_per_task_usd: float
    close_center_monthly_usd: float
    close_low_monthly_usd: float
    close_high_monthly_usd: float
    recommended_model_id: str | None
    recommended_model_name: str | None


class AnalyzeRequest(BaseModel):
    prompt_text: str = Field(..., min_length=10, max_length=100_000)
    tasks_per_day: int = Field(50, ge=1, le=10_000)
    apply_headroom: bool = False
    use_llm_classifier: bool = False
    classifier_spend_approved: bool = False


class AnalyzeResponse(BaseModel):
    complexity: ComplexityDimensionsRow
    workload_derived: WorkloadDerivedRow
    cost_ranges: CostRangeRow
    rationale: list[str]
    analyzer_source: str = "heuristic"
    headroom_note: str | None = None
    estimate: EstimateResponse
