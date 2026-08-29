#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""How long the editor waits for diagnostics.

A language server is not measured in throughput. It is measured against a
person typing. The client recomputes diagnostics on every change, so what
matters is a single question: **does the answer come back before the user
notices?**

Two thresholds are worth naming, and the table marks both:

* **~16 ms** — one frame. Under this, diagnostics feel instantaneous;
  squiggles move with the cursor.
* **~100 ms** — the limit of "the system is reacting instantly". Past it
  the editor feels laggy on every keystroke, and past a few hundred
  milliseconds people start turning the extension off.

Measured across document sizes, because an account-data file is not one
record. A BaaS onboarding batch is tens or hundreds, and the file only
ever grows while somebody is editing it. Each record is validated
against the message-type schema independently, so cost tracks record
count directly -- which is why the size column matters more here than
in a library benchmark.

Also measured: **completion and hover**, which are called on demand
rather than on every change but block the UI while they run, and the
**malformed path**, which is the state a document spends most of its
life in while being typed. A linter that is fast on valid input and slow
on invalid input is slow exactly when the editor calls it most.

Run::

    python benches/bench_diagnostics.py
    python benches/bench_diagnostics.py --json
    python benches/bench_diagnostics.py --quick     # what CI runs

Nothing here asserts a threshold: wall-clock is not comparable between
machines, and a flaky performance gate teaches people to ignore red. CI
runs ``--quick`` so a benchmark that has stopped compiling against the
current API fails the build instead of rotting into a file that reads as
verified and is not.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import acmt001_lsp.server as lsp_server  # noqa: E402

FRAME_MS = 16.0
INSTANT_MS = 100.0

#: One valid acmt.007.001.05 account-opening record. Kept complete on
#: purpose: a record missing fields short-circuits validation early and
#: measures the error path rather than the working one.
_RECORD = {
    "msg_id": "ACMT-MSG-0001",
    "creation_date_time": "2026-01-15T10:30:00",
    "process_id": "ACMT-PRC-0001",
    "account_id": "GB29NWBK60161331926819",
    "account_id_other": "VRTL-0001-0001",
    "account_currency": "EUR",
    "account_name": "Treasury Operating Account",
    "account_type_cd": "CACC",
    "account_servicer_bic": "NWBKGB2LXXX",
    "account_owner_name": "Acme Embedded Finance Ltd",
    "account_owner_country": "GB",
    "account_owner_lei": "5493001KJTIIGC8Y1R12",
    "org_full_legal_name": "Acme Embedded Finance Limited",
    "org_country_of_operation": "GB",
    "org_address_country": "GB",
    "org_address_town": "London",
    "org_id_lei": "5493001KJTIIGC8Y1R12",
    "org_id_other": "ACME-ORG-001",
    "status_cd": "RECE",
    "reason_cd": "RR04",
}


def build(records: int) -> str:
    """A document carrying ``records`` valid account records."""
    rows = []
    for i in range(records):
        row = dict(_RECORD)
        row["msg_id"] = f"ACMT-MSG-{i:05d}"
        row["account_id_other"] = f"VRTL-{i:04d}-0001"
        rows.append(row)
    return json.dumps(rows, indent=2)


def corrupt(text: str) -> str:
    """The same document mid-edit: a quote not yet closed."""
    return text.replace('"account_currency"', '"account_currency', 1)


# Passed as callables rather than wrapped in lambdas: CodeQL flags a
# lambda that only forwards to a callable, and it is right -- the wrapper
# adds a frame and says nothing. `hover_text` takes an argument, so it
# gets a partial rather than a lambda for the same reason.
ON_DEMAND = [
    ("completion_items", lsp_server.completion_items),
    ("hover_text", partial(lsp_server.hover_text, "account_servicer_bic")),
]


def _best(call, repeats: int) -> float:
    """Best-of timing after one untimed warm-up.

    The minimum is the least noisy estimator here; the mean follows
    whatever else the machine is doing. A language server's worst case
    matters too, but the floor is what tells you whether the design can
    be responsive at all.
    """
    call()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        samples.append(time.perf_counter() - start)
    return min(samples)


def _verdict(ms: float) -> str:
    if ms <= FRAME_MS:
        return "instant"
    if ms <= INSTANT_MS:
        return "fine"
    return "LAGGY"


def measure(size: int, repeats: int) -> dict:
    """Valid and mid-edit diagnostics latency for a ``size``-record doc."""
    valid = build(size)
    broken = corrupt(valid)
    good = _best(partial(lsp_server.compute_diagnostics, valid), repeats)
    bad = _best(partial(lsp_server.compute_diagnostics, broken), repeats)
    return {
        "records": size,
        "valid_ms": good * 1e3,
        "malformed_ms": bad * 1e3,
        "valid_verdict": _verdict(good * 1e3),
        "malformed_verdict": _verdict(bad * 1e3),
    }


def run(quick: bool) -> dict:
    sizes = [1, 10] if quick else [1, 10, 25, 50, 100]
    repeats = 2 if quick else 5
    on_demand = {
        name: _best(call, 20 if quick else 200) * 1e3
        for name, call in ON_DEMAND
    }
    return {
        "sizes": [measure(n, repeats) for n in sizes],
        "on_demand_ms": on_demand,
    }


def render(results: dict) -> None:
    print(
        f"  {'records':>8}{'valid ms':>11}{'':>10}"
        f"{'mid-edit ms':>14}{'':>10}"
    )
    for row in results["sizes"]:
        print(
            f"  {row['records']:>8}{row['valid_ms']:>11.2f}"
            f"{row['valid_verdict']:>10}"
            f"{row['malformed_ms']:>14.3f}{row['malformed_verdict']:>10}"
        )
    print(
        f"\n  instant <= {FRAME_MS:.0f} ms (one frame), "
        f"fine <= {INSTANT_MS:.0f} ms, LAGGY above."
    )
    rows = results["sizes"]
    laggy = [r for r in rows if r["valid_verdict"] == "LAGGY"]
    if laggy:
        print(
            f"  Diagnostics pass {INSTANT_MS:.0f} ms at "
            f"{laggy[0]['records']} records. Each record is validated "
            f"against the schema\n  independently, so this tracks record "
            f"count -- a large onboarding batch will feel slow on every "
            f"keystroke."
        )
    else:
        print(
            f"  No measured size crosses {INSTANT_MS:.0f} ms. Sizes above "
            f"one frame still feel responsive;\n  the frame threshold is "
            f"where squiggles stop tracking the cursor exactly."
        )
    print()
    for name, ms in results["on_demand_ms"].items():
        print(f"  {name:<20}{ms:>8.3f} ms   {_verdict(ms)}")
    print(
        "  These are called on demand rather than on every keystroke, but "
        "they block the UI while they run."
    )
    print(
        "\n  The mid-edit column is the document as it spends most of its "
        "life: a quote not yet\n  closed. JSON parsing fails immediately "
        "and no record is validated, so the state the\n  editor calls "
        "most often is also the cheapest -- the opposite of the usual "
        "trap."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--quick", action="store_true", help="small sizes, as CI runs"
    )
    args = parser.parse_args()

    results = run(quick=args.quick)
    if args.json:
        json.dump(results, sys.stdout, indent=1)
        print()
    else:
        render(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
