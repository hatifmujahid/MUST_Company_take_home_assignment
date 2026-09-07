# Case Study: AP Exception Autopilot

## User and problem

A small business's accounts-payable process (1-3 people touch AP, under 50 invoices/month).
The existing process is **not** manual end-to-end - it's already automated for the happy
path (clean invoice, matches a PO, standard GL code). The recurring pain is what happens
when a case isn't clean: missing POs, amount/quantity mismatches, duplicate submissions,
ambiguous GL coding, unclear approval ownership. Today, a human has to notice these by
inspection, with no structured diagnosis or suggested action.

**Evidence of pain:** per the target user's own estimate, roughly 10-20% of invoices hit an
exception, each costing 10-20 minutes of manual resolution time - at ~40 invoices/month,
that's ~4-8 exceptions/month, or roughly 1-2 hours/month of manual exception-firefighting.
Small in absolute terms (consistent with the business's scale), but recurring and
error-prone - exactly the kind of judgment-heavy manual work worth automating first.

## Current workflow map

| Stage | Today |
|---|---|
| Trigger | Invoice arrives by email/attachment |
| Input | Invoice file + PO/receipt records in the existing system |
| Judgment | Is this invoice clean, or does it need exception handling? |
| Tool | Existing automation handles clean cases end-to-end; exceptions fall through to a human |
| Approval | A human on the 1-3 person team decides how to resolve/route the exception |
| Output | Invoice is paid/recorded once resolved |
| Exception | Missing PO, mismatch, duplicate, ambiguous coding, unclear approver - caught by whoever happens to notice, with no structured diagnosis |

AP Exception Autopilot formalizes the "judgment" and "exception" rows with a structured
diagnosis and suggested action, and leaves "approval" and final "output" as human-owned.

## Scope decisions and non-goals

v1 deliberately does not: integrate live with QuickBooks/Xero/NetSuite (produces a standard
journal-import CSV instead); poll email/IMAP (uses a watched folder); do custom OCR on
scanned images (relies on Claude's document understanding plus `pdfplumber` for born-digital
PDFs - a scanned image is an explicit, visible failure case, not silently mishandled);
auto-approve or auto-pay anything; send Slack/email notifications; or handle multiple
currencies/entities. Full rationale in `docs/architecture.md`.

## Architecture and major trade-offs

Two separate, narrow Claude calls per invoice (extraction, then GL coding) rather than one
call that does everything - each is schema-validated independently, and matching/routing/
duplicate-detection are deterministic Python, not delegated to the model, because they have
exact right answers. Full detail in `docs/architecture.md`, including why the SDK's native
`output_config` structured-output feature was used instead of a tool-use workaround.

## Work delegated to AI, judgment retained by humans

See `docs/ai_collaboration_note.md` for the full breakdown of the two distinct AI roles in
this project (Claude Code as build tool vs. the Claude API as a runtime component) and what
was verified rather than trusted. Within the shipped system itself: Claude extracts and
codes; a human always makes the final call on anything flagged, and always personally
imports the CSV for clean invoices - nothing is auto-paid or auto-imported.

## Target-user checkpoint

[To be completed after the target user runs `setup.bat` then `run.bat` themselves without
live guidance, per the plan's Session 2 checkpoint - feedback and resulting changes will be
logged here as a feedback -> change table.]

## Measured results

- **Field accuracy: 79/80 (99%)** on the 12-case golden set, one real failure that turned
  out to be a defensible alternate GL-code answer the confidence threshold correctly caught
  (see `docs/evaluation.md`), not a system defect.
- **Cost: ~$0.012/invoice** measured (extraction + coding), well under the ~$0.02-0.05
  estimate used to plan this. At ~40 invoices/month that's roughly **$0.50/month in API
  cost** against an estimated 1-2 hours/month of manual exception-firefighting today -
  the ROI case doesn't depend on an optimistic cost estimate holding up.
- **The clearest single piece of evidence for why this is worth building, not just asking
  Claude directly:** on a $1.50-rounding-difference invoice within tolerance, the naive
  baseline flagged it as not ready to pay (no tolerance concept), while the engineered
  pipeline correctly cleared it - meaning naive LLM use would have created *more* manual
  review work than the automated system, not less. Full detail in `docs/evaluation.md`.

## Failures, changes, and results

- **Real bug found and fixed during build:** the first live smoke test crashed on every
  invoice (`'ThinkingBlock' object has no attribute 'text'`) because the code assumed the
  first content block in a Claude response was always the JSON text block. Fixed by
  scanning for the block with `type == "text"` instead of indexing by position. This is the
  clearest concrete "before/after" evidence in this project: before the fix, 0/12 test
  cases could process; after, the pipeline runs end-to-end.
- **Evaluation methodology corrected before it was ever run:** the original plan called for
  pinning `temperature=0` for the non-determinism check. Introspecting the SDK directly
  showed this model generation exposes no `temperature` parameter at all, so the eval
  measures natural variance under default sampling instead of a temperature comparison that
  isn't possible with this API. See `docs/evaluation.md`.
- **Full results:** `eval/results.md` - field accuracy vs. golden data, 3-run agreement
  rates, confidence calibration, cost/latency, and the baseline comparison against a naive
  single-prompt Claude use of the same data.
- **Limitations:** see `docs/evaluation.md`'s honest discussion of the confidence-calibration
  sample size, and the messy-layout extraction case's results.

## Next two-week iteration plan

`scripts/two_week_report.py` is already built and produces exactly the adoption/quality
report (touch rate, exception rate, exception-reason breakdown) that will run against real
production `run.jsonl` data once this is in daily use - shown against the eval set today as
a preview, not fabricated future numbers. In the first two weeks of real use, priorities are:

1. Watch the real exception rate and reason-code breakdown against the 10-20% baseline
   estimate - confirm or correct that number with real data.
2. Wire in an override-rate signal (did the human change a GL code or match decision the
   system suggested) - not present in v1, flagged explicitly in `scripts/two_week_report.py`.
3. Re-tune the 0.75 confidence threshold using real extraction/coding confidence data
   instead of the 12-case synthetic calibration, which is too small to be statistically
   confident about on its own.
4. If real invoice volume/format reveals a common exception type not in the current 12 test
   cases, add it to the golden set rather than letting the eval set go stale.
