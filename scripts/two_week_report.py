"""
Aggregates output/<date>/run.jsonl across a date range into adoption/quality metrics:
touch rate, exception rate, and override rate. This is the exact report the tool will
produce once it has been run in production for two weeks - shown here against whatever
run.jsonl data currently exists (eval or early real usage) as a preview, not fabricated
future data. Override rate requires a human to actually mark a suggestion as
changed/confirmed, which isn't wired into the CLI yet - see docs/case_study.md's next
iteration plan.

Usage: python scripts/two_week_report.py [--since YYYY-MM-DD] [--until YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_run_logs(output_dir: Path, since: date | None, until: date | None) -> list[dict]:
    entries = []
    for run_dir in sorted(output_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        try:
            run_date = datetime.strptime(run_dir.name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if since and run_date < since:
            continue
        if until and run_date > until:
            continue
        log_path = run_dir / "run.jsonl"
        if not log_path.exists():
            continue
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
    return entries


def summarize(entries: list[dict]) -> dict:
    total = len(entries)
    if total == 0:
        return {"total": 0}

    exceptions = sum(1 for e in entries if e["status"] == "EXCEPTION")
    failed = sum(1 for e in entries if e["status"] == "FAILED")
    clean = total - exceptions - failed
    reason_counts: dict[str, int] = {}
    for e in entries:
        for code in e.get("exception_reason_codes", []):
            reason_counts[code] = reason_counts.get(code, 0) + 1

    return {
        "total": total,
        "clean": clean,
        "exception_count": exceptions,
        "failed_count": failed,
        "exception_rate": round(exceptions / total, 3),
        "touch_rate": round((exceptions + failed) / total, 3),
        "reason_breakdown": reason_counts,
        "note_on_override_rate": (
            "Override rate (how often a human changed a system suggestion) requires a feedback "
            "hook that isn't wired into the CLI yet - see the next-iteration plan in docs/case_study.md."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", type=str, default=None)
    parser.add_argument("--until", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=str(ROOT / "output"))
    args = parser.parse_args()

    since = datetime.strptime(args.since, "%Y-%m-%d").date() if args.since else None
    until = datetime.strptime(args.until, "%Y-%m-%d").date() if args.until else None

    entries = load_run_logs(Path(args.output_dir), since, until)
    summary = summarize(entries)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
