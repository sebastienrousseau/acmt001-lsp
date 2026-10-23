# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Coverage-guided fuzzing of the document handlers with Atheris.

The server re-reads the whole document on every change, so anything an
editor can hold reaches these functions. Each input picks a real message
type and a document, either raw text or a JSON array built from fuzzed
records, and goes through the diagnostics, the record locator, the
mapping to lsprotocol types, and hover. Each must answer and never raise;
anything else is a crash libFuzzer reports and minimises.

Run (Linux x86_64, Python 3.12)::

    pip install --require-hashes -r requirements/fuzz.txt
    pip install --no-deps --no-build-isolation -e .
    python fuzz/fuzz_documents.py fuzz/corpus -max_total_time=60
"""

import json
import sys

import atheris

with atheris.instrument_imports():
    from acmt001 import services

    import acmt001_lsp.server as srv

MESSAGE_TYPES = [m["message_type"] for m in services.list_message_types()]
FIELDS = [
    "account_id",
    "account_servicer_bic",
    "org_id_lei",
    "account_owner_lei",
    "msg_id",
]


def _value(fdp: atheris.FuzzedDataProvider) -> object:
    choice = fdp.ConsumeIntInRange(0, 3)
    if choice == 0:
        return None
    if choice == 1:
        return fdp.ConsumeBool()
    if choice == 2:
        return fdp.ConsumeInt(8)
    return fdp.ConsumeUnicodeNoSurrogates(40)


def _records(fdp: atheris.FuzzedDataProvider) -> list[object]:
    out: list[object] = []
    for _ in range(fdp.ConsumeIntInRange(0, 3)):
        record: dict[str, object] = {}
        for _ in range(fdp.ConsumeIntInRange(0, 5)):
            key = fdp.PickValueInList(FIELDS)
            record[key + fdp.ConsumeUnicodeNoSurrogates(2)] = _value(fdp)
        out.append(record)
    return out


def _document(fdp: atheris.FuzzedDataProvider) -> str:
    if fdp.ConsumeBool():
        return fdp.ConsumeUnicodeNoSurrogates(4096)
    return json.dumps(_records(fdp), indent=fdp.PickValueInList([None, 2]))


def test_one_input(data: bytes) -> None:
    """Drive every document handler with one fuzzer input."""
    fdp = atheris.FuzzedDataProvider(data)
    message_type = fdp.PickValueInList(MESSAGE_TYPES)
    text = _document(fdp)
    diagnostics = srv.compute_diagnostics(text, message_type)
    assert all(d["line"] >= 0 for d in diagnostics)
    srv._to_lsp_diagnostics(diagnostics)
    assert all(line >= 0 for line in srv._record_line_offsets(text))
    word = fdp.ConsumeUnicodeNoSurrogates(32)
    hover = srv.hover_text(word, message_type)
    assert hover is None or isinstance(hover, str)


def main() -> None:
    """Hand the harness to libFuzzer."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
