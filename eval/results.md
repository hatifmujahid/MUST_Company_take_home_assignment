# Evaluation Results

Model: `claude-sonnet-5` | Test cases: 12 | Golden-set scoring: 1 pass over all 12 cases | Non-determinism spot-check: 3 reps on 3 representative cases (not all 12 - see note below)

**Scope note:** running all 12 cases 3x each plus the baseline (84+ Claude calls) was too slow to complete reliably in this environment. Golden-set accuracy below is scored from a single full pass; non-determinism is spot-checked on 3 representative cases (one clean/simple, one messy-layout, one over-tolerance mismatch) run 3 times each instead of all 12. This is a real scope reduction, not hidden.

**Note on non-determinism methodology:** this Anthropic SDK/model generation does not expose a `temperature` parameter on `messages.create` (verified by introspecting `message_create_params` directly - there is no `temperature`, `top_p`, or `top_k` field). The agreement rates below therefore measure real-world variance under the API's default sampling, not a temperature=0 vs default comparison as originally planned.

## Field accuracy vs. golden data

| Case | vendor_name | invoice_number | po_number | total | match_status | gl_code_primary | deterministic_reason_codes | overall_status | approver_name |
|---|---|---|---|---|---|---|---|---|---|
| TC01_clean_matched_simple | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a | n/a |
| TC02_clean_multiline_coding | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a | n/a |
| TC03_partial_quantity_mismatch | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a | n/a |
| TC04_missing_po | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | n/a | n/a |
| TC05_new_vendor_bad_po_reference | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a | n/a |
| TC06_messy_layout_rounding_tolerance | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a | n/a |
| TC07_duplicate_resubmission | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a | n/a |
| TC08_corrupted_unreadable | n/a | n/a | n/a | n/a | n/a | n/a | n/a | PASS | n/a |
| TC09_po_typo_fuzzy_match | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a | n/a |
| TC10_escalated_approver_routing | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a | PASS |
| TC11_amount_mismatch_over_tolerance | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a | n/a |
| TC12_over_all_approval_thresholds | PASS | PASS | PASS | PASS | PASS | PASS | PASS | n/a | PASS |

**Overall field accuracy: 79/80 (99%)**

## Agreement rate across 3 runs (non-determinism spot-check)

Cases spot-checked: TC01_clean_matched_simple, TC06_messy_layout_rounding_tolerance, TC11_amount_mismatch_over_tolerance

All 21 checked fields agreed across all runs for the 3 spot-checked cases.

## Confidence calibration (extraction confidence buckets)

| Bucket | Invoices in bucket |
|---|---|
| low(<0.6) | 0 |
| med(0.6-0.85) | 4 |
| high(>0.85) | 13 |

See docs/evaluation.md for the honest discussion of this calibration's limits with only 12 test cases - the bucket sizes here are too small to draw a statistically confident conclusion about whether low confidence really predicts errors; this is flagged, not hidden.

## Cost & latency

- Total Claude API calls (pipeline, this eval run): 34
- Total cost: $0.2091
- Average latency per call: 3361 ms
- Estimated cost per invoice (extract + code): $0.0123

## Baseline comparison: engineered pipeline vs. naive single-prompt Claude use

Both given the exact same invoice text and reference data (POs, receipts, chart of accounts, approvers).

| Case | Golden match_status | Pipeline match_status | Naive baseline ready_to_pay | Naive baseline issues (raw) |
|---|---|---|---|---|
| TC01_clean_matched_simple | MATCHED | MATCHED | True | None: invoice matches PO-1002 amount ($300.00) and receipt ($300.00), no duplica... |
| TC02_clean_multiline_coding | MATCHED | MATCHED | False | The invoice file provided is a binary/unreadable format and no text content coul... |
| TC03_partial_quantity_mismatch | PARTIAL | PARTIAL | False | Receipt on file for PO-1004 shows $700.00 received, but invoice total is $875.50... |
| TC04_missing_po | NO_PO_FOUND | NO_PO_FOUND | False | No matching purchase order on file for Quick Print Co (no PO number referenced o... |
| TC05_new_vendor_bad_po_reference | NO_PO_FOUND | NO_PO_FOUND | False | PO Number PO-9999 referenced on the invoice does not exist in our Purchase Order... |
| TC06_messy_layout_rounding_tolerance | MATCHED | MATCHED | False | Invoice total ($211.50) exceeds the matching PO-1009 amount ($210.00) and the on... |
| TC07_duplicate_resubmission | DUPLICATE | DUPLICATE | False | This invoice (Bright Cleaning Co / BC-2201) matches an entry in the previously p... |
| TC08_corrupted_unreadable | FAILED | FAILED | False | The invoice file is a binary/unreadable format, so no vendor name, invoice numbe... |
| TC09_po_typo_fuzzy_match | MATCHED | MATCHED | True | PO number on invoice was entered as 'PO-10O3' (letter O instead of digit 0), a l... |
| TC10_escalated_approver_routing | MATCHED | MATCHED | True | None - PO-1008 matches vendor and amount, receipt matches invoice total, no dupl... |
| TC11_amount_mismatch_over_tolerance | OVER_TOLERANCE | OVER_TOLERANCE | False | Invoice total ($2650.00) exceeds the matching PO-1005 amount ($2400.00) by $250.... |
| TC12_over_all_approval_thresholds | MATCHED | MATCHED | False | Invoice amount matches PO-1011 ($150,000.00) and matches the receipt on file ($1... |

The naive baseline has no fuzzy PO matching, no numeric tolerance logic, and no persistent duplicate ledger across invoices - any correct answers it gets on matching/duplicate cases come from the model reasoning it out unaided in one shot, with no code-level check. See docs/evaluation.md for a worked example of where this breaks down.
