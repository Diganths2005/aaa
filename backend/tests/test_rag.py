from services.rag import LocalKnowledgeRetriever, RetrievalFilter


def test_local_rag_retrieves_assessment_year_scoped_knowledge():
    results = LocalKnowledgeRetriever().retrieve(
        "Which ITR is selected for capital gains?",
        RetrievalFilter(user_id="user-1", assessment_year="2026-27"),
    )
    assert results
    assert any("ITR-2" in item.text for item in results)
    assert all(item.assessment_year == "2026-27" for item in results)


def test_local_rag_does_not_cross_assessment_years():
    assert LocalKnowledgeRetriever().retrieve(
        "capital gains",
        RetrievalFilter(user_id="user-1", assessment_year="2025-26"),
    ) == []