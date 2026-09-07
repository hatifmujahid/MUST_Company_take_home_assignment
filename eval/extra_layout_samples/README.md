# Extra layout-diversity samples

These 4 PDFs are **not part of the formal 12-case golden evaluation set** (`eval/test_cases/`
+ `eval/golden.json`) - they exist to stress-test extraction against visual layouts more
varied than the golden set's mostly-plain-text fixtures, since real invoices arrive in wildly
different formats (bordered tables, letterhead statements, minimalist freelancer invoices,
utility-bill-style statements).

Three of these reuse the *exact* underlying transaction from an existing golden case, just
re-rendered in a different visual style - so their correct answer is already known without
writing new golden labels:

| File | Same underlying case as | Visual style |
|---|---|---|
| `bordered_table_bright_cleaning.pdf` | `TC01_clean_matched_simple` | Bordered line-item table |
| `letterhead_remittance_northwind.pdf` | `TC09_po_typo_fuzzy_match` | Letterhead header + detachable remittance slip |
| `minimalist_vertex_marketing.pdf` | `TC11_amount_mismatch_over_tolerance` | Sparse single-line freelancer-style invoice |
| `utility_bill_citylink.pdf` | (new, no golden equivalent) | Multi-line-item utility/account-statement style, brand-new vendor with no PO on file - expect `NO_PO_FOUND` |

Why these exist instead of pulling files from a public GitHub "sample invoices" repo: the
obvious candidates either ship with no license at all (technically all-rights-reserved even
though the repo is public) or only bundle 1-2 generic table-extraction fixtures, not a
diverse real-world set. Generating our own avoids any licensing ambiguity. If real (redacted)
invoices become available, they belong here or in a similarly-labeled folder, not mixed into
the formal golden set unless golden labels are written for them too.
