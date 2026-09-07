# AP Exception Autopilot

Catches the accounts-payable exceptions a small business's existing automation lets slip
through - missing POs, amount mismatches, duplicate invoices, ambiguous GL coding, unclear
approval ownership - and hands you a plain-English digest instead of making you notice them
yourself. It never pays or imports anything automatically; you always review and act.

## Setup (one time)

1. Make sure Python 3.10+ is installed (check by opening a terminal and typing `python --version`; if that fails, get it from [python.org](https://www.python.org/downloads/)).
2. Double-click **`setup.bat`**. It creates an isolated environment, installs everything needed, and asks you to paste your Anthropic API key once (get one at [console.anthropic.com](https://console.anthropic.com)).
3. That's it. You won't need to touch `setup.bat` again unless something breaks.

## Daily use

1. Save invoice files (PDF, or plain text/email export) into the **`inbox`** folder - the same motion as saving an email attachment.
2. Double-click **`run.bat`**.
3. A digest opens automatically. The top line tells you how many are ready to pay and how many need you. Clean invoices are in `import_ready.csv`, ready to bring into your accounting software. Anything flagged is explained in one sentence in `exceptions.md`, with a suggested next step.

Full walkthrough, including what each exception type means and how to fix reference data: `docs/runbook.md`.

## What this is (and isn't)

- It never auto-pays or auto-imports anything - you always make the final call.
- It doesn't connect to QuickBooks/Xero/etc. directly - it produces a standard journal-import CSV you bring in yourself.
- It doesn't read your email inbox - you (or a proxy) drop files into the `inbox` folder.
- It doesn't do OCR on scanned images - born-digital PDFs and text/email exports only. A scanned image will show up as a "could not process" exception, not silently fail.

See `docs/case_study.md` for the full problem, design decisions, and evaluation behind this.

## Project layout

```
setup.bat / run.bat     - what a non-developer actually touches
src/ap_os/              - the pipeline: ingest -> extract -> match -> code -> route -> exceptions -> report
data/*.csv              - reference data (POs, receipts, chart of accounts, approvers) - synthetic in this repo
eval/                   - 12 golden test cases, evaluation harness, results
scripts/                - two-week production metrics rollup
docs/                   - architecture, case study, evaluation, runbook, AI collaboration note, demo script
```

## Developer quickstart (if you're not the non-developer user)

```
pip install -r requirements.txt
cp .env.example .env        # then paste your ANTHROPIC_API_KEY into it
cp config.example.yaml config.yaml
PYTHONPATH=src python -m ap_os run --dry-run   # wiring check, no API calls
PYTHONPATH=src python -m ap_os run             # real run against whatever's in inbox/
PYTHONPATH=src python eval/run_eval.py         # full evaluation suite -> eval/results.md
```
