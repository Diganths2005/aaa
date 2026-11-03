import json
from pathlib import Path

from services.ai_evaluation import SafetyCase, evaluate_answer, evaluate_cases
from services.knowledge import RetrievedContext, RetrievalFilter
from services.rag_pipeline import _rrf_fuse, _rerank
from services.rag_verification import verify_contexts


def test_hybrid_rrf_keeps_results_from_both_retrievers():
    a = RetrievedContext("section 87A rebate", "a.md", "2026-27", {"similarity": 0.9})
    b = RetrievedContext("rebate eligibility", "b.md", "2026-27", {"similarity": 0.8})
    fused = _rrf_fuse([[a], [b, a]])
    assert {item.source_name for item in fused} == {"a.md", "b.md"}


def test_reranker_prefers_query_term_overlap():
    weak = RetrievedContext("house property basics", "weak.md", "2026-27", {})
    strong = RetrievedContext("section 87A rebate eligibility", "strong.md", "2026-27", {"similarity": 0.4})
    result = _rerank("section 87A rebate", [weak, strong], 2)
    assert result[0].source_name == "strong.md"


def test_rule_version_verification_rejects_inactive_or_unproven_notes(tmp_path: Path):
    active = tmp_path / "active.md"
    active.write_text(
        '<!-- {"assessment_year":"2026-27","status":"active","source_files":["rule.py"]} -->\n# Rebate',
        encoding="utf-8",
    )
    inactive = tmp_path / "inactive.md"
    inactive.write_text(
        '<!-- {"assessment_year":"2026-27","status":"draft","source_files":["rule.py"]} -->\n# Draft',
        encoding="utf-8",
    )
    contexts = [
        RetrievedContext("active", "active.md", "2026-27", {"status": "active", "assessment_year": "2026-27", "source_files": ["rule.py"]}),
        RetrievedContext("draft", "inactive.md", "2026-27", {"status": "draft", "assessment_year": "2026-27", "source_files": ["rule.py"]}),
    ]
    verified = verify_contexts(contexts, assessment_year="2026-27", knowledge_root=tmp_path)
    assert verified[0].verified
    assert not verified[1].verified


def test_ai_safety_evaluation_rejects_unverified_number():
    case = SafetyCase(
        "What is my tax?",
        "Your tax is ₹999,999.",
        {"tax": 120000},
    )
    result = evaluate_answer(case, ["assessment-years/ay-2026-27.md"])
    assert not result.passed
    assert not result.numeric_grounded


def test_ai_safety_evaluation_accepts_grounded_answer():
    case = SafetyCase(
        "What is my tax?",
        "Your tax is ₹120,000 for AY 2026-27.",
        {"tax": 120000, "assessment_year": "2026-27"},
    )
    result = evaluate_answer(case, ["assessment-years/ay-2026-27.md"])
    assert result.passed


def test_ai_safety_evaluation_reports_rates():
    cases = [
        SafetyCase("q1", "Tax is ₹120,000.", {"tax": 120000}),
        SafetyCase("q2", "Tax is ₹999,999.", {"tax": 120000}),
    ]
    report = evaluate_cases(cases, {"q1": ["rule.md"], "q2": ["rule.md"]})
    assert report["cases"] == 2
    assert report["passed"] == 1
    assert report["numeric_grounding_rate"] == 0.5
