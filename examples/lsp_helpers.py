#!/usr/bin/env python3
"""Example: the LSP server's editor-feature helpers.

Usage:
    pip install acmt001-lsp     # requires Python 3.10+
    python examples/lsp_helpers.py

The acmt001 language server (launched as `acmt001-lsp` over stdio) powers
editor features for account-data JSON files. Its logic lives in pure helpers
that you can call directly — exactly what the server runs on each edit.
"""

import json

from acmt001_lsp.server import (
    completion_items,
    compute_diagnostics,
    hover_text,
)

# --- Diagnostics: a valid record vs. common mistakes ------------------------
valid_doc = json.dumps(
    [
        {
            "msg_id": "ACMT-MSG-0001",
            "creation_date_time": "2026-01-15T10:30:00",
            "process_id": "ACMT-PRC-0001",
            "account_id": "GB29NWBK60161331926819",
            "account_currency": "EUR",
            "account_name": "Treasury Operating Account",
            "account_type_cd": "CACC",
            "account_servicer_bic": "NWBKGB2LXXX",
            "account_owner_name": "Acme Embedded Finance Ltd",
            "account_owner_country": "GB",
            "org_full_legal_name": "Acme Embedded Finance Limited",
            "org_id_lei": "5493001KJTIIGC8Y1R12",
        }
    ]
)
print("valid document diagnostics:", compute_diagnostics(valid_doc))

missing = json.dumps([{"msg_id": "ONLY-ID"}])
print(
    "missing-fields diagnostics:",
    len(compute_diagnostics(missing)),
    "issue(s)",
)

bad_bic = json.dumps([{"account_servicer_bic": "INVALID"}])
print("bad-BIC diagnostics:       ", compute_diagnostics(bad_bic)[:1])

print("malformed JSON diagnostics:", compute_diagnostics("{not json"))

# --- Completion and hover ----------------------------------------------------
items = completion_items()
print(f"completion items:          {len(items)} (e.g. {items[0]['label']})")
print("hover account_servicer_bic:", hover_text("account_servicer_bic"))
print("hover unknown field:       ", hover_text("nope"))
