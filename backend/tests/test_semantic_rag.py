from unittest.mock import Mock

from services.knowledge import RetrievalFilter
from services.semantic_rag import SemanticKnowledgeBase


def test_stale_vectors_are_removed_only_for_current_user_and_year():
    collection = Mock()
    collection.get.side_effect = [
        {"ids": ["knowledge:stale", "knowledge:current"]},
        {"ids": ["user:user-1:stale", "user:user-1:current"]},
    ]
    records = [
        {"id": "knowledge:current", "source_type": "knowledge"},
        {"id": "user:user-1:current", "source_type": "user_document"},
    ]

    SemanticKnowledgeBase._remove_stale_records(
        collection,
        records,
        RetrievalFilter(assessment_year="2026-27", user_id="user-1"),
    )

    assert collection.get.call_args_list[0].kwargs["where"] == {
        "$and": [
            {"source_type": "knowledge"},
            {"assessment_year": "2026-27"},
        ]
    }
    assert collection.get.call_args_list[1].kwargs["where"] == {
        "$and": [
            {"source_type": "user_document"},
            {"user_id": "user-1"},
        ]
    }
    collection.delete.assert_any_call(ids=["knowledge:stale"])
    collection.delete.assert_any_call(ids=["user:user-1:stale"])
    assert collection.delete.call_count == 2
