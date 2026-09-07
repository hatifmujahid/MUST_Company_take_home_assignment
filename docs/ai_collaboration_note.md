# AI Collaboration Note

This project used AI in two genuinely different roles. Conflating them would misrepresent
what was verified and how - so they're kept separate throughout.

## Role 1: Claude Code as the build tool

Claude (via Claude Code, in an interactive session with the candidate) designed the
architecture, wrote the Python codebase (`src/ap_os/`), generated the synthetic reference
data and test fixtures, and wrote this documentation, under the candidate's direction and
review at every step.

**What was delegated:** first-draft architecture and module boundaries, pydantic schema
design, the Claude API integration code, the CLI/batch-file UX, the evaluation harness, and
the initial synthetic dataset (POs, receipts, approvers, chart of accounts, 12 test cases).

**What was verified, not trusted on sight:**
- Every module was actually run, not just read. A live smoke test on a real invoice
  surfaced a real bug within minutes: the code assumed `response.content[0]` was always the
  JSON text block, but this model generation can prepend a `ThinkingBlock` before the text
  block, causing `AttributeError: 'ThinkingBlock' object has no attribute 'text'` on every
  single invoice. Fixed by scanning `response.content` for the block with `type == "text"`
  instead of indexing by position (`src/ap_os/util.py::extract_json_text`).
- The plan's evaluation design originally called for pinning `temperature=0` to reduce
  non-determinism. Before writing that into the eval harness, the SDK was introspected
  directly (`inspect.getsource` on `message_create_params`) and confirmed this model
  generation's `messages.create` exposes no `temperature`, `top_p`, or `top_k` parameter at
  all. The eval methodology was corrected to measure natural variance under default
  sampling instead of claiming a temperature control that doesn't exist - see
  `docs/evaluation.md` for the honest version of this.
- The PO-typo fuzzy-matching cutoff (`difflib.get_close_matches(..., cutoff=0.8)`) was
  tuned empirically, not assumed: a two-character typo ("PO-1OO3") scored 0.667 similarity
  and correctly failed to match, while a one-character typo ("PO-10O3") scored 0.833 and
  correctly resolved to the right PO - both were tested against the full PO list before
  being locked into the golden test case, not just checked against the one case it was
  designed for.
- The full pipeline was run end-to-end on a real (non-fixture) invoice before any test
  cases were written, specifically to catch integration bugs that a curated golden set
  might not exercise.

**Decisions the candidate owned, not Claude:** the choice of accounts-payable exception
handling as the target workflow (over several other viable options considered); the v1
scope and every non-goal (no ERP integration, no OCR, no auto-payment); the confidence
threshold default (0.75) and where it routes; the 3-session pacing of the 5-day brief; and
the decision to build hardening (retries, reference-data validation, idempotency) in from
the start rather than as a separate later pass, with the trade-off that "before/after
regression" is demonstrated through real bugs caught during live testing (documented above
and in `docs/evaluation.md`) rather than a synthetic unhardened build kept around for
comparison.

## Role 2: the Claude API as a runtime component inside the shipped system

Separately from all of the above, `claude-sonnet-5` is called by the running tool itself,
twice per invoice - once to extract structured data, once to suggest GL coding - via
schema-enforced structured output (`output_config.format.json_schema`), not a tool-use
workaround.

**How this is verified:** not by trusting the model's self-reported confidence, but by
`eval/run_eval.py` scoring its actual output against `eval/golden.json`, whose expected
values were independently hand-computed from the reference data (PO amounts, tolerance
math, chart-of-accounts descriptions) - not derived by looking at what the model produced
and calling it correct. See `docs/evaluation.md` for the full results, including where this
verification found real limits (the confidence-calibration sample size, and the messy-layout
extraction case).
