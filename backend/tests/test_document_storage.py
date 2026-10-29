from pathlib import Path

from services.document_storage import DocumentStorage


def test_document_storage_is_user_and_document_isolated(tmp_path: Path):
    storage = DocumentStorage(tmp_path)
    key, digest = storage.save("user-1", "doc-1", "statement.pdf", b"hello")

    assert key == "user-1/doc-1/statement.pdf"
    assert storage.read(key) == b"hello"
    assert len(digest) == 64
    assert storage.exists(key)


def test_document_storage_rejects_path_escape(tmp_path: Path):
    storage = DocumentStorage(tmp_path)

    try:
        storage.path_for("../outside.pdf")
    except ValueError as exc:
        assert "escapes" in str(exc)
    else:
        raise AssertionError("path traversal should be rejected")


def test_document_storage_delete_is_idempotent(tmp_path: Path):
    storage = DocumentStorage(tmp_path)
    key, _ = storage.save("user-1", "doc-1", "statement.pdf", b"hello")
    storage.delete(key)
    storage.delete(key)
    assert not storage.exists(key)
