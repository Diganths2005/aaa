from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.knowledge import RetrievedContext


@dataclass(frozen=True)
class VerifiedSource:
    context: RetrievedContext
    verified: bool
    reason: str


def verify_contexts(
    contexts: list[RetrievedContext],
    *,
    assessment_year: str,
    knowledge_root: Path,
) -> list[VerifiedSource]:
    verified: list[VerifiedSource] = []
    for context in contexts:
        metadata: dict[str, Any] = dict(context.metadata)
        source_type = metadata.get("source_type", "knowledge")
        if source_type == "user_document":
            ok = metadata.get("document_status") in {
                "PROCESSED",
                "REQUIRES_CONFIRMATION",
                "CONFIRMED",
            }
            reason = "owner-scoped processed document"
        else:
            source_path = knowledge_root / context.source_name
            ok = (
                metadata.get("status") == "active"
                and metadata.get("assessment_year") == assessment_year
                and source_path.is_file()
            )
            source_files = metadata.get("source_files") or []
            if not source_files:
                ok = False
                reason = "knowledge note has no declared rule/source provenance"
            else:
                try:
                    import json
                    import re
                    note_text = source_path.read_text(encoding="utf-8")
                    match = re.match(r"\A<!--\s*(\{.*?\})\s*-->\s*", note_text, flags=re.DOTALL)
                    note_metadata = json.loads(match.group(1)) if match else {}
                    note_sources = note_metadata.get("source_files") or []
                    ok = ok and bool(note_sources)
                    ok = ok and all((knowledge_root.parent / item).exists() for item in note_sources)
                except (OSError, ValueError, json.JSONDecodeError):
                    ok = False
                reason = "active assessment-year note with verified source-file provenance" if ok else "declared source provenance could not be verified"

        if context.assessment_year not in (None, assessment_year):
            ok = False
            reason = "assessment-year mismatch"
        verified.append(VerifiedSource(context=context, verified=ok, reason=reason))
    return verified
