# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Language Server Protocol (LSP) server for Acmt001 account-data files.

This server helps developers author **acmt account-data JSON files** - a JSON
array of flat record objects (the same records that drive XML generation). It
provides three editor features, all backed by :mod:`acmt001.services` so they
behave identically to the CLI, REST API, and MCP server:

* **Diagnostics** - each record is validated against a message type's input
  JSON Schema, and any ``account_id`` / ``account_servicer_bic`` /
  ``org_id_lei`` / ``account_owner_lei`` values are additionally checked with
  the dedicated IBAN / BIC / LEI validators.
* **Completion** - every input field (with its description) plus the list of
  supported message types are offered as completion items.
* **Hover** - hovering a field name shows its schema description.

The intended message type defaults to ``acmt.007.001.05`` (Account Opening
Request); the pure helpers accept a ``message_type`` argument so a different
type can be configured.

Launching
---------
The package installs an ``acmt001-lsp`` console entry point (declared in
``pyproject.toml`` as ``acmt001.lsp.server:main``) which starts the server over
stdio::

    acmt001-lsp

Editor wiring
-------------
Point your editor's LSP client at the ``acmt001-lsp`` command for JSON files.
For Neovim (``nvim-lspconfig`` / the built-in ``vim.lsp.config`` API) register a
server whose ``cmd`` is ``{ "acmt001-lsp" }`` and ``filetypes`` includes
``"json"``. VS Code clients spawn the same command over stdio.

The business logic lives in pure, testable helper functions
(:func:`compute_diagnostics`, :func:`completion_items`, :func:`hover_text`); the
LSP handlers below are thin glue that map those plain dicts to ``lsprotocol``
types.
"""

from __future__ import annotations

import json
from typing import Any

from acmt001 import services
from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer

DEFAULT_MESSAGE_TYPE = "acmt.007.001.05"

# Flat-record fields whose values are financial identifiers, mapped to the
# identifier kind understood by ``services.validate_identifier``.
_IDENTIFIER_FIELDS = {
    "account_id": "iban",
    "account_servicer_bic": "bic",
    "org_id_lei": "lei",
    "account_owner_lei": "lei",
}


# ---------------------------------------------------------------------------
# Pure helpers (no LSP/server I/O - directly unit-testable)
# ---------------------------------------------------------------------------
def _normalise_records(parsed: Any) -> list[dict[str, Any]]:
    """Coerce parsed JSON into a list of record dicts.

    A single dict is treated as one record; a list is returned as-is.
    """
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return parsed
    return []


def _record_line_offsets(text: str) -> list[int]:
    """Best-effort mapping of record index -> line number.

    Uses the position of each top-level ``{`` opening brace. This is a heuristic
    (stdlib ``json`` does not expose offsets), but it lets diagnostics point at
    roughly the right record. Falls back to line 0 when a record cannot be
    located.
    """
    offsets: list[int] = []
    depth = 0
    in_string = False
    escaped = False
    line = 0
    for ch in text:
        if escaped:
            escaped = False
        elif ch == "\\" and in_string:
            escaped = True
        elif ch == '"':
            in_string = not in_string
        elif not in_string:
            if ch == "\n":
                line += 1
                continue
            if ch == "{":
                if depth == 0:
                    offsets.append(line)
                depth += 1
            elif ch == "}":
                depth = max(0, depth - 1)
        if ch == "\n":
            line += 1
    return offsets


def compute_diagnostics(
    text: str, message_type: str = DEFAULT_MESSAGE_TYPE
) -> list[dict]:
    """Compute diagnostics for an acmt account-data JSON document.

    Parses ``text`` as JSON (a list of record dicts, or a single dict treated as
    one record). On a JSON syntax error, returns a single diagnostic at line 0.
    For valid JSON, runs schema validation via
    :func:`acmt001.services.validate_records` and additionally checks any present
    identifier fields with :func:`acmt001.services.validate_identifier`.

    Args:
        text: The raw document text.
        message_type: The acmt message type to validate against.

    Returns:
        A list of plain dicts::

            {"line": int, "character": int,
             "severity": "error" | "warning", "message": str}
    """
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return [
            {
                "line": max(0, exc.lineno - 1),
                "character": max(0, exc.colno - 1),
                "severity": "error",
                "message": f"Invalid JSON: {exc.msg}",
            }
        ]

    records = _normalise_records(parsed)
    if not records:
        return [
            {
                "line": 0,
                "character": 0,
                "severity": "error",
                "message": (
                    "Expected a JSON array of record objects "
                    "(or a single record object)."
                ),
            }
        ]

    line_offsets = _record_line_offsets(text)

    def line_for(row: int) -> int:
        if 0 <= row < len(line_offsets):
            return line_offsets[row]
        return 0

    diagnostics: list[dict] = []

    # Schema validation (required fields, types, patterns, lengths, ...).
    report = services.validate_records(message_type, records)
    for err in report["errors"]:
        row = err.get("row", 0)
        path = err.get("path") or ""
        prefix = f"{path}: " if path else ""
        diagnostics.append(
            {
                "line": line_for(row),
                "character": 0,
                "severity": "error",
                "message": f"{prefix}{err['message']}",
            }
        )

    # Identifier validation (IBAN / BIC / LEI) for any present values.
    for row, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        for field, kind in _IDENTIFIER_FIELDS.items():
            value = record.get(field)
            if not value or not isinstance(value, str):
                continue
            if not services.validate_identifier(kind, value)["valid"]:
                diagnostics.append(
                    {
                        "line": line_for(row),
                        "character": 0,
                        "severity": "warning",
                        "message": (
                            f"{field}: {value!r} is not a valid "
                            f"{kind.upper()}."
                        ),
                    }
                )

    return diagnostics


def completion_items(
    message_type: str = DEFAULT_MESSAGE_TYPE,
) -> list[dict]:
    """Return completion items for an acmt account-data document.

    Offers every input field for ``message_type`` (with its schema description as
    the detail) plus every supported message type.

    Args:
        message_type: The acmt message type whose fields are offered.

    Returns:
        A list of ``{"label": str, "detail": str, "kind": "field"}`` dicts.
    """
    items: list[dict] = []
    properties = services.get_input_schema(message_type).get("properties", {})
    for field, spec in properties.items():
        items.append(
            {
                "label": field,
                "detail": (spec or {}).get("description", "") or "",
                "kind": "field",
            }
        )
    for entry in services.list_message_types():
        items.append(
            {
                "label": entry["message_type"],
                "detail": entry["name"],
                "kind": "field",
            }
        )
    return items


def hover_text(
    field: str, message_type: str = DEFAULT_MESSAGE_TYPE
) -> str | None:
    """Return the schema description for ``field``, or ``None``.

    Args:
        field: An input field name.
        message_type: The acmt message type whose schema is consulted.

    Returns:
        The field's ``description`` string, or ``None`` if the field is unknown
        or has no description.
    """
    properties = services.get_input_schema(message_type).get("properties", {})
    spec = properties.get(field)
    if not spec:
        return None
    description = spec.get("description")
    return description or None


# ---------------------------------------------------------------------------
# LSP glue (thin - maps plain dicts to lsprotocol types)
# ---------------------------------------------------------------------------
server = LanguageServer("acmt001-lsp", "v0.0.1")

_SEVERITY = {
    "error": lsp.DiagnosticSeverity.Error,
    "warning": lsp.DiagnosticSeverity.Warning,
}


def _to_lsp_diagnostics(raw: list[dict]) -> list[lsp.Diagnostic]:
    """Map plain diagnostic dicts to ``lsprotocol`` ``Diagnostic`` objects."""
    diagnostics: list[lsp.Diagnostic] = []
    for item in raw:
        line = item["line"]
        char = item["character"]
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=line, character=char),
                    end=lsp.Position(line=line, character=char),
                ),
                message=item["message"],
                severity=_SEVERITY.get(
                    item["severity"], lsp.DiagnosticSeverity.Error
                ),
                source="acmt001-lsp",
            )
        )
    return diagnostics


def _validate_and_publish(ls: LanguageServer, uri: str) -> None:
    """Compute diagnostics for ``uri`` and publish them to the client."""
    document = ls.workspace.get_text_document(uri)
    raw = compute_diagnostics(document.source)
    ls.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(
            uri=uri,
            diagnostics=_to_lsp_diagnostics(raw),
        )
    )


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(
    ls: LanguageServer, params: lsp.DidOpenTextDocumentParams
) -> None:
    """Publish diagnostics when a document is opened."""
    _validate_and_publish(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(
    ls: LanguageServer, params: lsp.DidChangeTextDocumentParams
) -> None:
    """Publish diagnostics when a document changes."""
    _validate_and_publish(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_COMPLETION)
def completion(
    ls: LanguageServer, params: lsp.CompletionParams
) -> lsp.CompletionList:
    """Offer input-field and message-type completions."""
    items = [
        lsp.CompletionItem(
            label=item["label"],
            detail=item["detail"],
            kind=lsp.CompletionItemKind.Field,
        )
        for item in completion_items()
    ]
    return lsp.CompletionList(is_incomplete=False, items=items)


@server.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(ls: LanguageServer, params: lsp.HoverParams) -> lsp.Hover | None:
    """Show the schema description for the field under the cursor."""
    document = ls.workspace.get_text_document(params.text_document.uri)
    word = document.word_at_position(params.position)
    if not word:
        return None
    text = hover_text(word)
    if text is None:
        return None
    return lsp.Hover(contents=text)


def main() -> None:
    """Start the ``acmt001-lsp`` language server over stdio."""
    server.start_io()


if __name__ == "__main__":
    main()
