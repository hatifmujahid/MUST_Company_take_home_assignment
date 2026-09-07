# Evaluation

Full raw output: `eval/results.md` (regenerate with `PYTHONPATH=src python eval/run_eval.py`).

## Methodology

- **Golden set:** 12 hand-designed test cases (`eval/test_cases/`, expected answers in
  `eval/golden.json`), covering clean matches, multi-line GL coding, partial-quantity
  mismatch, missing PO, a PO reference that doesn't exist, a deliberately messy/abbreviated
  layout, duplicate resubmission, a corrupted file, a single-character PO typo requiring
  fuzzy matching, escalated approver routing, an over-tolerance amount mismatch, and an
  amount exceeding every configured approver. Expected values were computed by hand from
  `data/pos.csv`/`receipts.csv`/`approvers.csv`/`chart_of_accounts.csv` - not by looking at
  what the model produced and calling it correct.
- **Baseline:** the same invoice text and reference data given to a single naive Claude
  prompt with no schema decomposition, no fuzzy matching code, no tolerance math, and no
  persistent duplicate ledger (`eval/baseline_naive.py`) - the "simple ChatGPT use" baseline
  the brief asks for, using the same underlying model both times so the comparison isolates
  engineering, not model quality.
- **Scope reduction, stated plainly:** the original plan called for running all 12 cases 3x
  each (temperature=0) to check non-determinism. Two things changed this: (1) introspecting
  the SDK showed this model generation exposes no `temperature`/`top_p`/`top_k` parameter on
  `messages.create` at all, so a temp=0 comparison isn't possible; (2) running all 12 cases
  3x plus the baseline (84+ sequential Claude calls) was too slow to complete reliably as a
  single pass in this environment. Golden-set accuracy is scored from **one full pass**;
  non-determinism is spot-checked on **3 representative cases run 3 times each** instead of
  all 12. This is a real reduction in coverage, disclosed here rather than hidden.

## Results summary

- **Field accuracy: 79/80 (99%)** across all 12 cases on the single full pass.
- **Non-determinism spot-check: 21/21 fields agreed** across 3 runs on the 3 spot-checked
  cases (clean/simple, messy-layout, over-tolerance mismatch) - encouraging, but a 3-case
  sample is not strong evidence of stability across the full input space.
- **Cost: ~$0.012/invoice** (extraction + coding, both Claude calls), ~$0.21 total for the
  full eval run (34 calls). Comfortably inside the plan's $0.02-0.05/invoice estimate.
- **Confidence calibration:** 0 low-confidence, 4 medium, 13 high extraction-confidence
  readings across all pipeline runs in this eval. With this few data points, this is not
  enough to statistically validate the 0.75 threshold - it's a starting point to re-tune
  once real production `run.jsonl` data accumulates (see `scripts/two_week_report.py`).

## The one field failure, and why it's more interesting than a bug

`TC04_missing_po`'s GL coding was scored FAIL because the model assigned `6500 Marketing &
Advertising` to "business card printing," while `eval/golden.json` had predicted `6900
Miscellaneous Expense` (with `6100 Office Supplies` also marked acceptable). The model's own
rationale: *"Business card printing is a marketing/branding material expense... rather than
general office supplies since it's promotional print material from a print vendor."* That's
a genuinely defensible third answer I hadn't anticipated when writing the golden set - not a
model error, but a limitation of the golden set's coverage of legitimate ambiguity. Two
things are worth noting about how the system actually handled this: the coding confidence
came back at **0.65**, below the 0.75 threshold, so this line item was correctly routed to
`LOW_CONFIDENCE_CODING` for human review rather than silently applying an uncertain code.
The safety net worked even though the specific answer wasn't the one predicted.

## Predicted vs. actual failure modes (Day 4 requirement)

Three failure categories were predicted before running the eval:

1. **Extraction misread on messy layout** - predicted, tested via `TC06`. **Did not
   materialize as expected**: the deliberately abbreviated/shorthand invoice was extracted
   correctly (all fields passed, confidence landed in the medium/high range, not low). This
   is worth taking with real caution - one messy fixture I wrote is not a strong test of
   real-world layout variance, and this is exactly the kind of case that should be re-tested
   against actual scanned/forwarded invoices once real samples are available.
2. **False-positive exception on a borderline-but-fine invoice** - predicted, and this
   surfaced, but in the **baseline, not the pipeline**: on `TC06` (invoice $211.50 vs. PO
   $210.00, a $1.50 rounding difference inside the $5 tolerance), the naive baseline
   answered `ready_to_pay: False`, flagging a perfectly fine invoice as a mismatch because it
   has no concept of tolerance. The engineered pipeline correctly cleared it as `MATCHED`.
   This is the single clearest, most concrete piece of evidence in this eval for why the
   engineered system is worth it over "just ask Claude": the naive approach would create
   *more* manual review work, not less, on an invoice that needed none.
3. **GL miscoding on an ambiguous vendor** - predicted, and this is exactly what happened
   with `TC04` above, caught correctly by the confidence threshold.

## Where the baseline comparison reveals something not initially planned for

`TC02_clean_multiline_coding` is a PDF fixture (used specifically to exercise real PDF
ingestion). The naive baseline script only extracts text for `.txt` files, so it correctly
reported it couldn't read a raw PDF - passing along the same limitation a person would hit
pasting an unprocessed PDF into a chat window. This wasn't scored as a baseline "failure";
it's a real, honest illustration that "just use ChatGPT" still requires a human to handle
file conversion themselves, which the engineered pipeline's `pdfplumber` integration does
automatically. Left as-is rather than "fixed" by feeding the baseline pre-extracted text,
since that would make the comparison less representative of how someone actually uses a
chat interface with a PDF attachment.

## Layout-diversity stress test (supplementary, not part of the 12-case golden score)

`eval/extra_layout_samples/` re-renders 3 known transactions (already in the golden set) in
visually unrelated formats - a bordered line-item table, a colored letterhead with a
detachable remittance slip, and a sparse single-line freelancer invoice - plus one brand-new
utility-bill-style document with no golden equivalent. Since 3 of these have already-known
correct answers, this is a genuine extraction-robustness check, not just a demo prop.

**Result: 4/4 correct.** All three known-answer cases extracted the right vendor, total, and
PO (including the `PO-10O3` fuzzy-match typo, this time behind a colored header block and a
dashed remittance-slip divider) and reproduced the exact same match/GL-coding outcome as
their plainer originals. The new utility-bill case correctly triggered `NO_PO_FOUND` (no PO
exists for utility accounts) and its GL confidence came back at 0.4 - correctly below
threshold, since a 3-line electric/water/waste bill doesn't map cleanly to a single account
in the current chart of accounts. This is a small sample (4 documents) and shouldn't be read
as proof of general layout robustness, but it's meaningfully more evidence than the single
messy-layout case in the formal golden set, and found no new failure mode.

## Honest limitations

- 12 test cases and one full pass is not a statistically powerful sample - the 99% field
  accuracy number should be read as "no significant defects found in this set," not "99%
  accurate in production."
- The confidence-calibration bucket counts are too small to confirm or reject whether 0.75
  is the right threshold - real usage data is the actual test, tracked from day one via
  `scripts/two_week_report.py`.
- Non-determinism was spot-checked on 3 of 12 cases, not all 12, for the reasons stated above.
- The naive baseline was only asked to decide once per case (not run 3x), since its purpose
  here is a single reference point for "what would happen without the engineering," not a
  full second evaluation subject.
