# Demo Script (5 minutes, screen-recorded)

Record this yourself - it has to be a real screen capture, not something generated. Rough
timing below; adjust to what actually happens on your screen.

## 0:00-0:45 - The problem and baseline

- Say it plainly: "Our AP process is already automated for clean invoices, but roughly
  10-20% hit an exception - missing PO, amount mismatch, duplicate, unclear coding - and
  each one costs 10-20 minutes of manual chasing today. That's the bottleneck this fixes."
- Show `docs/case_study.md`'s workflow-map table for 3 seconds - trigger/input/judgment/
  tool/approval/output/exception - to make the "already automated except for exceptions"
  point visually, not just verbally.

## 0:45-2:30 - Live flow, real input to output

- Show the `inbox` folder empty (or with prior files already processed/moved out).
- Drag 3-4 real invoice files in (mix of clean, a mismatch, a duplicate if you have one).
- Double-click `run.bat` on camera - let the terminal window actually run.
- The digest opens automatically - read the top-line banner out loud ("X processed, Y need
  attention").
- Open `exceptions.md` and read one exception's plain-English explanation and suggested
  action out loud.
- Open `import_ready.csv` and show it's a normal-looking journal import, not a JSON dump.

## 2:30-3:15 - The non-developer user experience

- Point out explicitly: "I never typed a command. Setup was one double-click and pasting an
  API key once. Daily use is: drop files in, double-click, read the digest."
- Mention the one real limitation here: Python has to already be on the machine, or someone
  runs `setup.bat` once during handoff.

## 3:15-4:15 - Evaluation and failure handling

- Open `eval/results.md`. Call out three numbers: overall field accuracy, the baseline
  comparison table (naive single-prompt Claude vs. this pipeline), and the non-determinism
  agreement rate.
- Show one real failure case and its root cause (e.g. the messy-layout extraction case, or
  the `ThinkingBlock` bug found and fixed during build - see `docs/evaluation.md`).
- Show a corrupted file being dropped in and processed without crashing the batch - one of
  the 12 golden cases (`TC08_corrupted_unreadable.pdf`) exists specifically to demonstrate this.

## 4:15-5:00 - Measured results and the most important limitation

- State the cost/time number plainly: "$X per invoice in API cost, versus Y minutes of
  manual exception-handling today."
- State the single most important limitation honestly - most likely one of: extraction
  confidence on messy/unusual invoice layouts, the small golden-set size limiting how much
  the confidence-calibration numbers can be trusted, or that override-rate tracking (did a
  human actually change a suggestion) isn't wired in yet.
- Close with the next-iteration plan from `docs/case_study.md` in one sentence.
