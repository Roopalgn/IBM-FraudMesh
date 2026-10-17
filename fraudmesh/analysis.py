"""Computed component response with review policy; no raw local rows accepted."""
from fraudmesh.integration import build_analysis_response
from fraudmesh.triage import annotate_analysis


def analyze_signals(signals: list[dict]) -> dict:
    return annotate_analysis(build_analysis_response(signals), signals)
