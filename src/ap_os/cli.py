from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from .config import load_config
from .pipeline import run_pipeline
from .schemas import ProcessingStatus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ap_os", description="AP Exception Autopilot")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Process every invoice currently in the inbox folder.")
    run_p.add_argument("--dry-run", action="store_true", help="Validate wiring without calling the Claude API.")
    run_p.add_argument("--no-open", action="store_true", help="Don't auto-open the digest when done.")

    args = parser.parse_args(argv)

    if args.command == "run":
        return _run(dry_run=args.dry_run, open_digest=not args.no_open)

    return 1


def _run(dry_run: bool, open_digest: bool) -> int:
    cfg = load_config(Path.cwd())
    results = run_pipeline(cfg, dry_run=dry_run)

    if not results:
        print("No invoices found in the inbox folder. Drop some files in and run again.")
        return 0

    clean = sum(1 for r in results if r.status == ProcessingStatus.CLEAN)
    exception = sum(1 for r in results if r.status == ProcessingStatus.EXCEPTION)
    failed = sum(1 for r in results if r.status == ProcessingStatus.FAILED)
    print(f"Processed {len(results)} invoice(s): {clean} clean, {exception} flagged, {failed} failed.")

    if dry_run:
        print("(dry run - no Claude API calls were made, no reports were written)")
        return 0

    from datetime import date

    digest_path = cfg.paths.output / date.today().isoformat() / "digest.md"
    print(f"Digest written to {digest_path}")

    if open_digest and digest_path.exists():
        webbrowser.open(digest_path.resolve().as_uri())

    return 0


if __name__ == "__main__":
    sys.exit(main())
