from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    error = "error"
    warning = "warning"
    info = "info"


class ValidationIssue(BaseModel):
    code: str
    severity: Severity
    message: str
    path: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(issue.severity == Severity.error for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity == Severity.warning for issue in self.issues)

    @property
    def ok(self) -> bool:
        return self.error_count == 0


class LoadedDocument(BaseModel):
    role: str
    path: str
    content: str
    chars: int

    @classmethod
    def from_path(cls, role: str, path: Path) -> "LoadedDocument":
        content = path.read_text(encoding="utf-8")
        return cls(role=role, path=str(path), content=content, chars=len(content))
