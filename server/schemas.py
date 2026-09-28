"""JSON shapes for API endpoints — contracts between client and server."""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, example="What is an API?")


class AskResponse(BaseModel):
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    tokens_used: int
    cost_usd: float


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
