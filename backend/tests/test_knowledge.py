import pytest
from pathlib import Path
from services.knowledge import LocalTaxKnowledgeBase, RetrievalFilter, chunk_text


def test_knowledge_retrieval_is_assessment_year_scoped():
    retriever = LocalTaxKnowledgeBase()
    filters = RetrievalFilter(assessment_year="2026-27")

    results = retriever.retrieve("How is the rebate calculated?", filters)

    assert results
    assert any(item.source_name == "concepts/rebate.md" for item in results)
    assert results[0].source_name == "concepts/rebate.md"
    assert all(item.source_name != "income/salary.md" for item in results)
    assert all(item.assessment_year == "2026-27" for item in results)


def test_knowledge_retrieval_returns_no_context_for_unknown_year_or_topic():
    retriever = LocalTaxKnowledgeBase()

    assert retriever.retrieve("How is the rebate calculated?", RetrievalFilter("2025-26")) == []
    assert retriever.retrieve("How is cryptocurrency taxed?", RetrievalFilter("2026-27")) == []


def test_knowledge_retrieval_can_use_a_temporary_note_root(tmp_path: Path):
    note = tmp_path / "topic.md"
    note.write_text(
        '<!-- {"assessment_year":"2026-27","status":"active","topic":"example"} -->\n\n# Rebate\n\nThe rebate is calculated by the verified engine.\n',
        encoding="utf-8",
    )

    results = LocalTaxKnowledgeBase(tmp_path).retrieve("rebate", RetrievalFilter("2026-27"))

    assert len(results) == 1
    assert results[0].source_name == "topic.md"


def test_knowledge_retrieval_ranks_topic_relevant_passages_first():
    results = LocalTaxKnowledgeBase().retrieve(
        "How does section 87A rebate work?",
        RetrievalFilter(assessment_year="2026-27"),
    )

    assert results
    assert results[0].source_name == "concepts/rebate.md"


def test_chunk_text_bounds_passages_and_retains_overlap():
    text = "alpha " * 300
    chunks = chunk_text(text, max_chars=80, overlap=12)

    assert len(chunks) > 1
    assert all(len(chunk) <= 80 for chunk in chunks)
    assert all(left[-12:].split()[-1] in right for left, right in zip(chunks, chunks[1:]))


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("text", max_chars=10, overlap=10)