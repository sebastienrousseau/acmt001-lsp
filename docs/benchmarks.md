# Benchmarks

A language server is not measured in throughput. It is measured against
a person typing: the client recomputes diagnostics on every change, so
the only question that matters is whether the answer comes back before
the user notices.

Two thresholds are worth naming:

| Threshold | Meaning |
|-----------|---------|
| ~16 ms | One frame. Squiggles move with the cursor; feels instantaneous. |
| ~100 ms | The limit of "reacting instantly". Past this the editor feels laggy on every keystroke. |

## Running it

```sh
python benches/bench_diagnostics.py           # full run
python benches/bench_diagnostics.py --quick   # what CI runs
python benches/bench_diagnostics.py --json    # machine-readable
```

CI runs `--quick`. That is not a timing gate — wall-clock is not
comparable between runners, and a flaky performance gate teaches people
to ignore red. It exists so a benchmark that has stopped compiling
against the current API fails the build rather than rotting into a file
that reads as verified and is not.

## What it measures

**Diagnostics across document sizes.** An account-data file is not one
record; a BaaS onboarding batch is tens or hundreds, and the file only
grows while somebody edits it. Each record is validated against the
schema independently, so cost tracks record count almost directly. On a
2026 laptop a single record lands near 2 ms, and the 100 ms budget is
crossed somewhere around a hundred records — at which point every
keystroke in that buffer costs a visible pause.

**The mid-edit path.** A document spends most of its life syntactically
broken — a quote not yet closed. JSON parsing fails immediately and no
record is validated, so this path costs microseconds rather than
milliseconds. That is the opposite of the usual trap, where a linter is
fast on valid input and slow on the invalid input it is actually handed
most often.

**Completion and hover.** Called on demand rather than on every change,
but they block the UI while they run. Both sit far inside one frame.

## Reading the output

The table marks each measurement `instant`, `fine`, or `LAGGY` against
the two thresholds above. Nothing asserts a threshold: the verdict is
there to be read, not to fail a build on a busy runner.
