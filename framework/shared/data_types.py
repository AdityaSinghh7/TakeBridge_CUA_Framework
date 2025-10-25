"""Shared data models used across orchestrator and worker components."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class SharedState:
    """Container for durable notes that planners and workers should surface."""

    important_notes: List[str] = field(default_factory=list)

    def add_note(self, note: str) -> None:
        """Append a normalized note if it is non-empty."""
        normalized = note.strip()
        if normalized:
            self.important_notes.append(normalized)

