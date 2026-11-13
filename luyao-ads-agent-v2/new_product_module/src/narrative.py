from __future__ import annotations

from .schemas import PipelineResult


def generate_rationale(pipeline_result: PipelineResult) -> dict:
    """Return deterministic structured rationale.

    The SOP allows an LLM only to rewrite existing structured results into
    natural language. The first version deliberately does not call an LLM, so
    no score, threshold comparison, ranking, or conclusion can be changed here.
    """

    return pipeline_result.model_dump()
