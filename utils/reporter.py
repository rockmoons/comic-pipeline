"""Reporter: generate structured validation reports."""

import json
from dataclasses import dataclass, field, asdict
from enum import Enum


class Status(Enum):
    PASS = "✅"
    FAIL = "❌"
    WARN = "⚠️"
    FATAL = "🔴"

    def to_json(self) -> str:
        return self.name.lower()


@dataclass
class CheckResult:
    layer: str
    num: int
    name: str
    status: Status
    detail: str = ""
    fix_hint: str = ""


@dataclass
class ValidationReport:
    timestamp: str = ""
    style: str = ""
    chapter: str = ""
    results: List[CheckResult] = field(default_factory=list)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.status == Status.PASS)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.status == Status.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for r in self.results if r.status == Status.WARN)

    @property
    def fatal_count(self) -> int:
        return sum(1 for r in self.results if r.status == Status.FATAL)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 100.0
        return (self.pass_count / self.total) * 100


def format_report(report: ValidationReport) -> str:
    """Generate formatted terminal report."""
    lines = []
    sep = "═" * 56

    lines.append(sep)
    lines.append(f"  Comic Pipeline 校验报告 v1.0")
    lines.append(f"  时间：{report.timestamp}")
    lines.append(f"  视觉风格：{report.style} | 章节：{report.chapter}")
    lines.append(sep)

    # Group by layer
    layers = {}
    for r in report.results:
        if r.layer not in layers:
            layers[r.layer] = []
        layers[r.layer].append(r)

    for layer_name, items in layers.items():
        lines.append(f"\n{layer_name} ({len(items)}项)")
        lines.append("─" * 56)
        for r in items:
            status_str = r.status.value
            num_str = f"{r.num:02d}"
            line = f"{status_str} {num_str} {r.name:<30s}"
            if r.detail:
                line += f" {r.detail}"
            lines.append(line)
            if r.fix_hint:
                lines.append(f"      → {r.fix_hint}")

    lines.append(f"\n{sep}")
    fatal_str = f"  致命问题：{report.fatal_count}" if report.fatal_count > 0 else ""
    lines.append(f"  结果：{report.pass_count} ✅ / {report.fail_count} ❌ / {report.warn_count} ⚠️")
    lines.append(f"  通过率：{report.pass_rate:.1f}%")
    if fatal_str:
        lines.append(f"  {fatal_str}")
    lines.append(sep)

    return '\n'.join(lines)


def format_json(report: ValidationReport) -> str:
    """Generate JSON report for CI/machine consumption."""
    data = {
        "timestamp": report.timestamp,
        "style": report.style,
        "chapter": report.chapter,
        "summary": {
            "total": report.total,
            "pass": report.pass_count,
            "fail": report.fail_count,
            "warn": report.warn_count,
            "fatal": report.fatal_count,
            "pass_rate": round(report.pass_rate, 1),
        },
        "results": []
    }
    for r in report.results:
        data["results"].append({
            "layer": r.layer,
            "num": r.num,
            "name": r.name,
            "status": r.status.to_json(),
            "detail": r.detail,
            "fix_hint": r.fix_hint,
        })
    return json.dumps(data, ensure_ascii=False, indent=2)
