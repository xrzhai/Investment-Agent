from __future__ import annotations

import json
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from harness.models import Severity, ValidationIssue
from harness.research.models import FactRecord, FactStatus, ResearchStatus, SourceRecord
from harness.settings import HarnessPaths


_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,31}$")


class ResearchStore:
    """File-backed research records with legacy coverage compatibility."""

    def __init__(self, paths: HarnessPaths | None = None):
        self.paths = paths or HarnessPaths.discover()

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()
        if not _SYMBOL_RE.fullmatch(normalized):
            raise ValueError(f"invalid symbol: {symbol!r}")
        return normalized

    def symbol_dir(self, symbol: str) -> Path:
        return self.paths.coverage / self.normalize_symbol(symbol)

    def record_path(self, symbol: str, relative_path: str) -> Path:
        root = self.symbol_dir(symbol).resolve(strict=False)
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise ValueError(f"research record path must be relative: {relative_path!r}")
        resolved = (root / candidate).resolve(strict=False)
        if root not in resolved.parents:
            raise ValueError(f"research record path escapes symbol directory: {relative_path!r}")
        return resolved

    def list_symbols(self) -> list[str]:
        if not self.paths.coverage.exists():
            return []
        return sorted(
            path.name
            for path in self.paths.coverage.iterdir()
            if path.is_dir() and _SYMBOL_RE.fullmatch(path.name.upper())
        )

    def current_thesis_path(self, symbol: str) -> Path | None:
        root = self.symbol_dir(symbol)
        pointer = root / "current.md"
        if not pointer.exists():
            return None
        target = pointer.read_text(encoding="utf-8").strip()
        if not target:
            return None
        if Path(target).name != target or not target.lower().endswith(".md"):
            raise ValueError(f"unsafe current thesis pointer for {symbol}: {target!r}")
        resolved = (root / target).resolve(strict=False)
        if resolved.parent != root.resolve(strict=False):
            raise ValueError(f"current thesis pointer escapes symbol directory: {target!r}")
        return resolved if resolved.exists() else None

    def load_current_thesis(self, symbol: str) -> tuple[Path, str] | None:
        path = self.current_thesis_path(symbol)
        if path is None:
            return None
        return path, path.read_text(encoding="utf-8")

    def load_status(self, symbol: str) -> ResearchStatus:
        normalized = self.normalize_symbol(symbol)
        root = self.symbol_dir(normalized)
        path = root / "status.json"
        if path.exists():
            return ResearchStatus.model_validate_json(path.read_text(encoding="utf-8"))

        thesis = self.current_thesis_path(normalized)
        summary_path = "README.md" if (root / "README.md").exists() else "summary.md"
        legacy_layout = thesis is not None or (root / "README.md").exists()
        return ResearchStatus(
            symbol=normalized,
            current_thesis=thesis.name if thesis else None,
            summary_path=summary_path,
            coverage_stage="legacy" if legacy_layout else "building",
            legacy_layout=legacy_layout,
        )

    def load_summary(self, symbol: str, status: ResearchStatus | None = None) -> tuple[Path | None, str]:
        status = status or self.load_status(symbol)
        root = self.symbol_dir(symbol)
        candidates = [self.record_path(symbol, status.summary_path), root / "summary.md", root / "README.md"]
        seen: set[Path] = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            if path.exists() and path.is_file():
                return path, path.read_text(encoding="utf-8")
        return None, ""

    def load_sources(self, symbol: str, status: ResearchStatus | None = None) -> list[SourceRecord]:
        status = status or self.load_status(symbol)
        path = self.record_path(symbol, status.sources_path)
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw.get("sources", []) if isinstance(raw, dict) else raw
        return [SourceRecord.model_validate(item) for item in items]

    def load_facts(
        self,
        symbol: str,
        *,
        status: ResearchStatus | None = None,
        tags: Iterable[str] | None = None,
        as_of: date | None = None,
        include_statuses: set[FactStatus] | None = None,
        include_other_symbols: bool = False,
        limit: int | None = None,
    ) -> list[FactRecord]:
        status = status or self.load_status(symbol)
        path = self.record_path(symbol, status.facts_path)
        if not path.exists():
            return []
        def normalize_tag(value: str) -> str:
            return re.sub(r"\s+", " ", re.sub(r"[_-]+", " ", value.strip().lower()))

        wanted_tags = {normalize_tag(tag) for tag in tags or [] if tag.strip()}
        wanted_statuses = include_statuses or {FactStatus.active, FactStatus.disputed, FactStatus.unverified}
        candidates: list[FactRecord] = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = FactRecord.model_validate_json(line)
            except ValidationError as exc:
                raise ValueError(f"invalid fact at {path}:{line_no}: {exc}") from exc
            if not include_other_symbols and record.symbol.upper() != self.normalize_symbol(symbol):
                continue
            if as_of:
                available = record.available_at or record.recorded_at
                available_date = available.date() if isinstance(available, datetime) else available
                if available_date > as_of:
                    continue
            candidates.append(record)

        superseded_ids = {record.supersedes for record in candidates if record.supersedes}
        records: list[FactRecord] = []
        for record in candidates:
            effective = (
                record.model_copy(update={"status": FactStatus.superseded})
                if record.fact_id in superseded_ids and record.status == FactStatus.active
                else record
            )
            if effective.status not in wanted_statuses:
                continue
            if wanted_tags:
                record_tags = {normalize_tag(tag) for tag in effective.tags}
                matched = any(
                    wanted == actual
                    or f" {actual} " in f" {wanted} "
                    or f" {wanted} " in f" {actual} "
                    for wanted in wanted_tags
                    for actual in record_tags
                )
                if not matched:
                    continue
            records.append(effective)
        records.sort(key=lambda item: item.recorded_at, reverse=True)
        return records if limit is None else records[:limit]

    def add_source(self, symbol: str, source: SourceRecord) -> bool:
        """Add one source atomically; identical retries are idempotent."""

        normalized = self.normalize_symbol(symbol)
        if source.local_path:
            self.record_path(normalized, source.local_path)
        self.ensure_scaffold(normalized)
        status = self.load_status(normalized)
        path = self.record_path(normalized, status.sources_path)
        existing = self.load_sources(normalized, status)
        by_id = {item.source_id: item for item in existing}
        if source.source_id in by_id:
            if by_id[source.source_id] == source:
                return False
            raise ValueError(f"source_id already exists with different content: {source.source_id}")
        payload = {
            "schema_version": "1",
            "sources": [item.model_dump(mode="json") for item in [*existing, source]],
        }
        self._atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        return True

    def append_fact(self, symbol: str, fact: FactRecord) -> bool:
        """Append one sourced fact atomically without rewriting prior facts."""

        normalized = self.normalize_symbol(symbol)
        if fact.symbol.upper() != normalized:
            raise ValueError(f"fact symbol {fact.symbol!r} does not match {normalized}")
        self.ensure_scaffold(normalized)
        status = self.load_status(normalized)
        sources_by_id = {source.source_id: source for source in self.load_sources(normalized, status)}
        missing_sources = sorted(set(fact.source_ids) - set(sources_by_id))
        if missing_sources:
            raise ValueError(f"fact references missing sources: {missing_sources}")
        available = fact.available_at or fact.recorded_at
        available_date = available.date() if isinstance(available, datetime) else available
        for source_id in fact.source_ids:
            published = sources_by_id[source_id].published_at
            published_date = published.date() if isinstance(published, datetime) else published
            if published_date and published_date > available_date:
                raise ValueError(f"fact available_at precedes source publication: {source_id}")

        existing = self.load_facts(
            normalized,
            status=status,
            include_statuses=set(FactStatus),
            include_other_symbols=True,
        )
        by_id = {item.fact_id: item for item in existing}
        if fact.fact_id in by_id:
            comparison = by_id[fact.fact_id].model_copy(update={"status": fact.status})
            if comparison == fact:
                return False
            raise ValueError(f"fact_id already exists with different content: {fact.fact_id}")
        if fact.supersedes:
            prior = by_id.get(fact.supersedes)
            if prior is None:
                raise ValueError(f"superseded fact does not exist: {fact.supersedes}")
            if prior.fact_key != fact.fact_key:
                raise ValueError("a fact may supersede only the same fact_key")

        path = self.record_path(normalized, status.facts_path)
        old_text = path.read_text(encoding="utf-8") if path.exists() else ""
        prefix = old_text if not old_text or old_text.endswith("\n") else old_text + "\n"
        self._atomic_write(path, prefix + fact.model_dump_json() + "\n")
        return True

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(content)
                handle.flush()
                temporary = Path(handle.name)
            temporary.replace(path)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()

    def ensure_scaffold(self, symbol: str, company_name: str = "") -> list[Path]:
        """Create missing structured research files without changing thesis history."""
        normalized = self.normalize_symbol(symbol)
        root = self.symbol_dir(normalized)
        root.mkdir(parents=True, exist_ok=True)
        thesis = self.current_thesis_path(normalized)
        created: list[Path] = []

        status_path = root / "status.json"
        if not status_path.exists():
            payload = ResearchStatus(
                symbol=normalized,
                company_name=company_name,
                coverage_stage="legacy" if thesis is not None else "building",
                current_thesis=thesis.name if thesis else None,
                summary_path="summary.md",
                facts_path="facts.jsonl",
                sources_path="sources.json",
                legacy_layout=thesis is not None,
            )
            status_path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
            created.append(status_path)

        for filename, content in (
            ("facts.jsonl", ""),
            ("sources.json", json.dumps({"schema_version": "1", "sources": []}, indent=2, ensure_ascii=False)),
        ):
            path = root / filename
            if not path.exists():
                path.write_text(content, encoding="utf-8")
                created.append(path)

        summary_path = root / "summary.md"
        if not summary_path.exists():
            current_name = thesis.name if thesis else "not initiated"
            stage = "Legacy migration required" if thesis else "Building"
            header = (
                f"# {normalized} — 价值投资研究摘要\n\n"
                f"**当前 Thesis：** `{current_name}`\n"
                f"**覆盖状态：** {stage}\n"
                "**估值状态：** Missing\n"
                f"**生成时间：** {datetime.now(timezone.utc).isoformat()}\n\n"
            )
            summary_path.write_text(
                header
                + "## 当前理解\n\n"
                + "[Agent：自由概括这门生意、价值来源、价格隐含预期和最大疑点。]\n\n"
                + "## 最重要的依据\n\n"
                + "- 尚未完成结构化迁移；请只保留最能支持或挑战判断的证据。\n\n"
                + "## 估值读法\n\n"
                + "[Agent：选择适合该公司的方法，说明日期、区间和敏感假设。]\n\n"
                + "## 下一步\n\n"
                + "[Agent：写下一项最可能改变判断的证据或问题。]\n",
                encoding="utf-8",
            )
            created.append(summary_path)
        return created

    def validate_symbol(self, symbol: str) -> list[ValidationIssue]:
        normalized = self.normalize_symbol(symbol)
        root = self.symbol_dir(normalized)
        issues: list[ValidationIssue] = []
        if not root.exists():
            return [ValidationIssue(code="research.symbol_missing", severity=Severity.error, message=f"missing coverage directory for {normalized}", path=str(root))]

        try:
            current = self.current_thesis_path(normalized)
        except ValueError as exc:
            issues.append(ValidationIssue(code="research.current_pointer_unsafe", severity=Severity.error, message=str(exc), path=str(root / "current.md")))
            current = None
        if current is None:
            issues.append(ValidationIssue(code="research.current_thesis_missing", severity=Severity.error, message=f"{normalized} has no resolvable current thesis", path=str(root / "current.md")))

        try:
            status = self.load_status(normalized)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            issues.append(ValidationIssue(code="research.status_invalid", severity=Severity.error, message=str(exc), path=str(root / "status.json")))
            return issues

        for field_name in ("summary_path", "facts_path", "sources_path"):
            relative = getattr(status, field_name)
            try:
                self.record_path(normalized, relative)
            except ValueError as exc:
                issues.append(ValidationIssue(code="research.record_path_unsafe", severity=Severity.error, message=str(exc), path=str(root / "status.json"), details={"field": field_name}))
        if status.current_thesis and Path(status.current_thesis).name != status.current_thesis:
            issues.append(ValidationIssue(code="research.status_thesis_path_unsafe", severity=Severity.error, message="status current_thesis must be a filename in the symbol directory", path=str(root / "status.json")))

        if status.current_thesis and current and status.current_thesis != current.name:
            issues.append(ValidationIssue(code="research.status_pointer_mismatch", severity=Severity.error, message="status.json and current.md point to different thesis versions", path=str(root / "status.json")))
        if status.legacy_layout:
            issues.append(ValidationIssue(code="research.legacy_layout", severity=Severity.info, message="structured research migration is incomplete; legacy coverage remains the active fallback", path=str(root)))
        else:
            if status.valuation_status not in {"current", "stale", "missing"}:
                issues.append(
                    ValidationIssue(
                        code="research.valuation_status_invalid",
                        severity=Severity.warning,
                        message=f"unknown valuation_status: {status.valuation_status!r}",
                        path=str(root / "status.json"),
                    )
                )
            elif status.valuation_status != "current":
                issues.append(
                    ValidationIssue(
                        code="research.valuation_not_current",
                        severity=Severity.warning,
                        message=f"active coverage valuation is {status.valuation_status}; refresh dated market and estimate inputs before a valuation-dependent decision",
                        path=str(root / "status.json"),
                    )
                )
            elif status.valuation_as_of is None:
                issues.append(
                    ValidationIssue(
                        code="research.valuation_date_missing",
                        severity=Severity.warning,
                        message="valuation_status is current but valuation_as_of is missing; treat freshness as uncertain",
                        path=str(root / "status.json"),
                    )
                )

        try:
            sources = self.load_sources(normalized, status)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            issues.append(ValidationIssue(code="research.sources_invalid", severity=Severity.error, message=str(exc), path=str(root / status.sources_path)))
            sources = []
        sources_by_id = {source.source_id: source for source in sources}
        source_ids = set(sources_by_id)
        if len(source_ids) != len(sources):
            issues.append(ValidationIssue(code="research.source_id_duplicate", severity=Severity.error, message="duplicate source_id values", path=str(root / status.sources_path)))
        for source in sources:
            if source.local_path:
                try:
                    self.record_path(normalized, source.local_path)
                except ValueError as exc:
                    issues.append(ValidationIssue(code="research.source_path_unsafe", severity=Severity.error, message=str(exc), path=str(root / status.sources_path), details={"source_id": source.source_id}))

        try:
            facts = self.load_facts(
                normalized,
                status=status,
                include_statuses=set(FactStatus),
                include_other_symbols=True,
            )
        except ValueError as exc:
            issues.append(ValidationIssue(code="research.facts_invalid", severity=Severity.error, message=str(exc), path=str(root / status.facts_path)))
            facts = []
        fact_ids: set[str] = set()
        facts_by_id = {fact.fact_id: fact for fact in facts}
        for fact in facts:
            if fact.symbol.upper() != normalized:
                issues.append(ValidationIssue(code="research.fact_symbol_mismatch", severity=Severity.error, message=f"fact {fact.fact_id} belongs to {fact.symbol}, expected {normalized}", path=str(root / status.facts_path)))
            if fact.fact_id in fact_ids:
                issues.append(ValidationIssue(code="research.fact_id_duplicate", severity=Severity.error, message=f"duplicate fact_id: {fact.fact_id}", path=str(root / status.facts_path)))
            fact_ids.add(fact.fact_id)
            missing = sorted(set(fact.source_ids) - source_ids)
            if missing:
                issues.append(ValidationIssue(code="research.fact_source_missing", severity=Severity.error, message=f"fact {fact.fact_id} references missing sources: {missing}", path=str(root / status.facts_path)))
            available = fact.available_at or fact.recorded_at
            available_date = available.date() if isinstance(available, datetime) else available
            for source_id in set(fact.source_ids) & source_ids:
                published = sources_by_id[source_id].published_at
                published_date = published.date() if isinstance(published, datetime) else published
                if published_date and published_date > available_date:
                    issues.append(ValidationIssue(code="research.fact_before_source", severity=Severity.error, message=f"fact {fact.fact_id} is available before source {source_id} was published", path=str(root / status.facts_path)))
            if fact.supersedes:
                prior = facts_by_id.get(fact.supersedes)
                if prior is None:
                    issues.append(ValidationIssue(code="research.superseded_fact_missing", severity=Severity.error, message=f"fact {fact.fact_id} supersedes missing fact {fact.supersedes}", path=str(root / status.facts_path)))
                elif prior.fact_key != fact.fact_key:
                    issues.append(ValidationIssue(code="research.supersedes_key_mismatch", severity=Severity.error, message=f"fact {fact.fact_id} supersedes a different fact_key", path=str(root / status.facts_path)))
        return issues
