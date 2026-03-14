# @grace.module grace.bootstrap_safety
# @grace.purpose Build deterministic bootstrap readiness reports so agents can decide whether a repository is safe for immediate scaffold apply or still needs extension work.
# @grace.interfaces BootstrapSafetyIssue, BootstrapSafetyReport, evaluate_bootstrap_safety
# @grace.invariant Bootstrap safety remains derived-only; it explains bootstrap readiness from existing policy, adapter, and discovery rules without mutating files or changing parser semantics.

from __future__ import annotations

from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grace.adapter_tools import probe_adapter
from grace.bootstrapper import discover_bootstrap_candidates
from grace.file_policy import GraceFilePolicyVerdict
from grace.repo_config import candidate_in_repo_scope, load_repo_config


# @grace.anchor grace.bootstrap_safety.BootstrapSafetyIssue
# @grace.complexity 2
class BootstrapSafetyIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    verdict: str
    issue_kind: str
    reason: str


# @grace.anchor grace.bootstrap_safety.BootstrapSafetyReport
# @grace.complexity 2
class BootstrapSafetyReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requested_path: Path
    file_count: int
    safe_file_count: int
    verdict_counts: dict[str, int]
    issue_counts: dict[str, int]
    safe_to_apply: bool
    issues: tuple[BootstrapSafetyIssue, ...] = Field(default_factory=tuple)


def _candidate_paths(path: Path) -> tuple[Path, ...]:
    resolved_path = path.expanduser().resolve()
    repo_config = load_repo_config(resolved_path)

    if resolved_path.is_file():
        return (resolved_path,)

    candidates: list[Path] = []
    for candidate in sorted(resolved_path.rglob("*")):
        if not candidate.is_file():
            continue
        if not candidate_in_repo_scope(repo_config, resolved_path, candidate.resolve()):
            continue
        candidates.append(candidate.resolve())
    return tuple(candidates)


def _issue_kind_for_verdict(verdict: str) -> str | None:
    if verdict == GraceFilePolicyVerdict.PREVIEW_ONLY.value:
        return "preview_only"
    if verdict == GraceFilePolicyVerdict.UNSUPPORTED.value:
        return "unsupported"
    if verdict == GraceFilePolicyVerdict.IGNORE.value:
        return "ignored"
    return None


# @grace.anchor grace.bootstrap_safety.evaluate_bootstrap_safety
# @grace.complexity 5
# @grace.belief Bootstrap should report readiness as a deterministic safety matrix over the existing repository policy and adapter boundary, so agents know whether they can apply scaffolds now or must extend support first.
def evaluate_bootstrap_safety(path: str | Path) -> BootstrapSafetyReport:
    requested_path = Path(path).expanduser().resolve()
    candidates = _candidate_paths(requested_path)
    probes = tuple(probe_adapter(candidate) for candidate in candidates)

    safe_paths = set()
    try:
        safe_paths = set(discover_bootstrap_candidates(requested_path))
    except ValueError:
        safe_paths = set()

    issues: list[BootstrapSafetyIssue] = []
    verdict_counts = Counter(probe.policy_verdict for probe in probes)
    for probe in probes:
        issue_kind = _issue_kind_for_verdict(probe.policy_verdict)
        if issue_kind is None:
            if probe.path not in safe_paths:
                issues.append(
                    BootstrapSafetyIssue(
                        path=probe.path,
                        verdict=probe.policy_verdict,
                        issue_kind="blocked_safe_apply",
                        reason="file is policy-safe but not discoverable by bootstrap candidate rules",
                    )
                )
            continue
        issues.append(
            BootstrapSafetyIssue(
                path=probe.path,
                verdict=probe.policy_verdict,
                issue_kind=issue_kind,
                reason=probe.reason,
            )
        )

    issues.sort(key=lambda item: item.path.as_posix())
    issue_counts = Counter(issue.issue_kind for issue in issues)
    safe_file_count = sum(1 for probe in probes if probe.path in safe_paths)

    return BootstrapSafetyReport(
        requested_path=requested_path,
        file_count=len(probes),
        safe_file_count=safe_file_count,
        verdict_counts=dict(sorted(verdict_counts.items())),
        issue_counts=dict(sorted(issue_counts.items())),
        safe_to_apply=not issues and len(probes) == len(safe_paths),
        issues=tuple(issues),
    )


__all__ = ["BootstrapSafetyIssue", "BootstrapSafetyReport", "evaluate_bootstrap_safety"]
