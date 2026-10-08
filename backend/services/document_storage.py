from __future__ import annotations

import hashlib
import os
from pathlib import Path

DEFAULT_STORAGE_ROOT = Path(os.getenv("DOCUMENT_STORAGE_DIR", ".taxwise-data/documents")).expanduser()


class DocumentStorage:
    """Persistent, user-isolated document storage."""

    def __init__(self, root: Path | str = DEFAULT_STORAGE_ROOT):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_component(value: str) -> str:
        value = str(value).strip()
        if not value or value in {".", ".."} or "/" in value or chr(92) in value:
            raise ValueError("Invalid storage path component")
        return value

    def key_for(self, user_id: str, document_id: str, filename: str) -> str:
        user = self._safe_component(user_id)
        document = self._safe_component(document_id)
        name = Path(filename).name
        if not name or name in {".", ".."}:
            raise ValueError("Invalid filename")
        return str(Path(user) / document / name)

    def path_for(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if self.root != candidate and self.root not in candidate.parents:
            raise ValueError("Storage key escapes document storage root")
        return candidate

    def save(self, user_id: str, document_id: str, filename: str, content: bytes) -> tuple[str, str]:
        key = self.key_for(user_id, document_id, filename)
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key, hashlib.sha256(content).hexdigest()

    def read(self, storage_key: str) -> bytes:
        return self.path_for(storage_key).read_bytes()

    def exists(self, storage_key: str) -> bool:
        return self.path_for(storage_key).is_file()

    def delete(self, storage_key: str) -> None:
        path = self.path_for(storage_key)
        path.unlink(missing_ok=True)
        parent = path.parent
        if parent != self.root and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                pass

    @staticmethod
    def sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
