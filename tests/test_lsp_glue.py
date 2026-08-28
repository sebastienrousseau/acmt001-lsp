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

"""The LSP glue, and the line-offset heuristic underneath the diagnostics.

`test_lsp_server.py` covers the pure helpers. Everything the editor actually
talks to — the four `@server.feature` handlers, the mapping to `lsprotocol`
types, and `main` — went untested, which is how the module sat at 73%.

That split matters more than the number. The helpers return plain dicts, so a
mistake there fails an assertion. The glue is where a wrong `line` becomes a
diagnostic pointing at the wrong record in someone's editor, and nothing
raises: the squiggle just sits under the wrong brace.

The stubs mirror `camt053-lsp`'s, so the two suites read the same way.
"""

import json

import pytest

pytest.importorskip("pygls")

from lsprotocol import types as lsp  # noqa: E402

import acmt001_lsp.server as lsp_server  # noqa: E402
from acmt001_lsp import __version__  # noqa: E402


# ---------------------------------------------------------------------------
# Lightweight stubs for the handlers (no live server, no stdio).
# ---------------------------------------------------------------------------
class _FakeDocument:
    """Minimal stand-in for a pygls text document."""

    def __init__(self, source: str, word: str = "") -> None:
        self.source = source
        self._word = word

    def word_at_position(self, position) -> str:  # noqa: ANN001
        return self._word


class _FakeWorkspace:
    def __init__(self, document: _FakeDocument) -> None:
        self._document = document

    def get_text_document(self, uri: str) -> _FakeDocument:
        return self._document


class _FakeLanguageServer:
    """Records published diagnostics; exposes a fake workspace."""

    def __init__(self, document: _FakeDocument) -> None:
        self.workspace = _FakeWorkspace(document)
        self.published: list = []

    def text_document_publish_diagnostics(
        self, params
    ) -> None:  # noqa: ANN001
        self.published.append(params)


def _did_open_params(uri: str = "file:///accounts.json"):
    return lsp.DidOpenTextDocumentParams(
        text_document=lsp.TextDocumentItem(
            uri=uri, language_id="json", version=1, text=""
        )
    )


def _did_change_params(uri: str = "file:///accounts.json"):
    return lsp.DidChangeTextDocumentParams(
        text_document=lsp.VersionedTextDocumentIdentifier(uri=uri, version=2),
        content_changes=[],
    )


def _hover_params(uri: str = "file:///accounts.json"):
    return lsp.HoverParams(
        text_document=lsp.TextDocumentIdentifier(uri=uri),
        position=lsp.Position(line=0, character=0),
    )


# ---------------------------------------------------------------------------
# _record_line_offsets — the heuristic that decides where a squiggle lands
# ---------------------------------------------------------------------------
class TestRecordLineOffsets:
    """Each record's line is found by tracking top-level ``{``.

    A brace inside a string, or a nested object, must not be mistaken for the
    start of a record — that shifts every subsequent diagnostic onto the wrong
    line, silently.
    """

    def test_one_record_per_line(self):
        text = '[\n{"a": 1},\n{"b": 2}\n]'
        assert lsp_server._record_line_offsets(text) == [1, 2]

    def test_a_nested_object_is_not_a_new_record(self):
        # The inner brace is at depth 1, so it must not add an offset.
        text = '[\n{"a": {"nested": 1}},\n{"b": 2}\n]'
        assert lsp_server._record_line_offsets(text) == [1, 2]

    def test_a_brace_inside_a_string_is_ignored(self):
        text = '[\n{"a": "not { a record"},\n{"b": 2}\n]'
        assert lsp_server._record_line_offsets(text) == [1, 2]

    def test_an_escaped_quote_does_not_end_the_string(self):
        # Without the escape branch, the \" closes the string and the
        # following brace is counted as a record.
        text = '[\n{"a": "he said \\" { here"},\n{"b": 2}\n]'
        assert lsp_server._record_line_offsets(text) == [1, 2]

    def test_newlines_inside_a_string_still_advance_the_line(self):
        # A literal newline in a JSON string is not legal, but the scanner is
        # a heuristic over raw text and must not lose count if it meets one.
        text = '[\n{"a": "x\ny"},\n{"b": 2}\n]'
        offsets = lsp_server._record_line_offsets(text)
        assert offsets[0] == 1
        assert offsets[1] > offsets[0]

    def test_a_stray_closing_brace_does_not_go_negative(self):
        # depth is clamped at 0; without the clamp the next top-level brace
        # would be seen as nested and produce no offset at all.
        text = '}\n{"a": 1}'
        assert lsp_server._record_line_offsets(text) == [1]

    def test_empty_text_has_no_offsets(self):
        assert lsp_server._record_line_offsets("") == []


# ---------------------------------------------------------------------------
# compute_diagnostics — the branches the happy path never reaches
# ---------------------------------------------------------------------------
class TestDiagnosticsEdges:
    @pytest.mark.parametrize("payload", ["42", '"a string"', "true", "null"])
    def test_json_that_is_not_records_is_refused(self, payload):
        """Valid JSON that is not an object or array of them."""
        diagnostics = lsp_server.compute_diagnostics(payload)
        assert len(diagnostics) == 1
        assert diagnostics[0]["severity"] == "error"
        assert "array of record objects" in diagnostics[0]["message"]

    def test_an_empty_array_is_refused(self):
        diagnostics = lsp_server.compute_diagnostics("[]")
        assert len(diagnostics) == 1
        assert "array of record objects" in diagnostics[0]["message"]

    def test_a_non_dict_element_is_skipped_by_identifier_checks(
        self, sample_record
    ):
        """A list mixing a record with a scalar must not raise.

        Schema validation will complain about the scalar; the identifier pass
        has to step over it rather than call ``.get`` on an int.
        """
        text = json.dumps([sample_record, 42])
        diagnostics = lsp_server.compute_diagnostics(text)
        # No warning can be attributed to the scalar, and the call returned.
        assert all(d["severity"] in {"error", "warning"} for d in diagnostics)

    def test_a_row_beyond_the_located_records_falls_back_to_line_zero(self):
        """``line_for`` clamps rather than indexing out of range.

        A record supplied as a bare dict has one brace to find, but an error
        reported against a row the scanner never located must still produce a
        usable position.
        """
        # A single record with a bad IBAN: the offsets list has one entry, and
        # asking for anything past it returns 0.
        assert lsp_server._record_line_offsets("{}") == [0]
        diagnostics = lsp_server.compute_diagnostics(
            json.dumps({"account_id": "NOT-AN-IBAN"})
        )
        assert all(d["line"] >= 0 for d in diagnostics)

    def test_a_non_string_identifier_value_is_not_validated(
        self, sample_record
    ):
        """``account_id: 12345`` is a schema error, not an IBAN warning.

        Passing an int to the IBAN validator would either raise or report a
        second, confusing diagnostic about a value the user can already see is
        the wrong type.
        """
        record = dict(sample_record)
        record["account_id"] = 12345
        diagnostics = lsp_server.compute_diagnostics(json.dumps([record]))
        assert not [
            d
            for d in diagnostics
            if d["severity"] == "warning" and "account_id" in d["message"]
        ]

    def test_an_empty_identifier_value_is_not_validated(self, sample_record):
        """An empty string is absent, not invalid."""
        record = dict(sample_record)
        record["org_id_lei"] = ""
        diagnostics = lsp_server.compute_diagnostics(json.dumps([record]))
        assert not [
            d
            for d in diagnostics
            if d["severity"] == "warning" and "org_id_lei" in d["message"]
        ]


# ---------------------------------------------------------------------------
# _to_lsp_diagnostics — plain dicts to lsprotocol types
# ---------------------------------------------------------------------------
class TestToLspDiagnostics:
    def test_an_error_maps_to_a_zero_width_range_at_the_position(self):
        [diagnostic] = lsp_server._to_lsp_diagnostics(
            [
                {
                    "line": 3,
                    "character": 7,
                    "severity": "error",
                    "message": "boom",
                }
            ]
        )
        assert diagnostic.severity == lsp.DiagnosticSeverity.Error
        assert diagnostic.message == "boom"
        assert diagnostic.source == "acmt001-lsp"
        assert diagnostic.range.start == lsp.Position(line=3, character=7)
        assert diagnostic.range.end == diagnostic.range.start

    def test_a_warning_maps_to_the_warning_severity(self):
        [diagnostic] = lsp_server._to_lsp_diagnostics(
            [
                {
                    "line": 0,
                    "character": 0,
                    "severity": "warning",
                    "message": "check this",
                }
            ]
        )
        assert diagnostic.severity == lsp.DiagnosticSeverity.Warning

    def test_an_unknown_severity_falls_back_to_error(self):
        """Better to over-report than to drop a diagnostic on the floor."""
        [diagnostic] = lsp_server._to_lsp_diagnostics(
            [
                {
                    "line": 0,
                    "character": 0,
                    "severity": "wat",
                    "message": "unknown",
                }
            ]
        )
        assert diagnostic.severity == lsp.DiagnosticSeverity.Error

    def test_an_empty_list_maps_to_an_empty_list(self):
        assert lsp_server._to_lsp_diagnostics([]) == []


# ---------------------------------------------------------------------------
# The handlers the editor actually calls
# ---------------------------------------------------------------------------
class TestHandlers:
    def test_did_open_publishes_diagnostics_for_a_bad_document(self):
        ls = _FakeLanguageServer(_FakeDocument("[{not json}]"))
        lsp_server.did_open(ls, _did_open_params())

        [params] = ls.published
        assert params.uri == "file:///accounts.json"
        assert len(params.diagnostics) == 1
        assert "Invalid JSON" in params.diagnostics[0].message

    def test_did_open_publishes_an_empty_list_for_a_good_document(
        self, sample_record
    ):
        """The empty publish is what clears a stale squiggle.

        Skipping it when there is nothing to report would leave the previous
        run's diagnostics on screen after the user fixed the file.
        """
        ls = _FakeLanguageServer(_FakeDocument(json.dumps([sample_record])))
        lsp_server.did_open(ls, _did_open_params())

        [params] = ls.published
        assert params.diagnostics == []

    def test_did_change_publishes_too(self):
        ls = _FakeLanguageServer(_FakeDocument("[]"))
        lsp_server.did_change(ls, _did_change_params())

        [params] = ls.published
        assert len(params.diagnostics) == 1

    def test_completion_offers_fields_and_message_types(self):
        ls = _FakeLanguageServer(_FakeDocument(""))
        result = lsp_server.completion(ls, None)

        assert result.is_incomplete is False
        labels = {item.label for item in result.items}
        assert "msg_id" in labels
        assert any(label.startswith("acmt.") for label in labels)
        assert all(
            item.kind == lsp.CompletionItemKind.Field for item in result.items
        )

    def test_hover_returns_the_schema_description(self):
        ls = _FakeLanguageServer(
            _FakeDocument("", word="account_servicer_bic")
        )
        result = lsp_server.hover(ls, _hover_params())

        assert result is not None
        assert isinstance(result.contents, str)
        assert result.contents

    def test_hover_on_an_unknown_word_returns_none(self):
        ls = _FakeLanguageServer(_FakeDocument("", word="not_a_field"))
        assert lsp_server.hover(ls, _hover_params()) is None

    def test_hover_on_no_word_returns_none(self):
        """The cursor sits on whitespace or punctuation."""
        ls = _FakeLanguageServer(_FakeDocument("", word=""))
        assert lsp_server.hover(ls, _hover_params()) is None


# ---------------------------------------------------------------------------
# Module wiring
# ---------------------------------------------------------------------------
class TestWiring:
    def test_main_starts_the_server_over_stdio(self, monkeypatch):
        started = []
        monkeypatch.setattr(
            lsp_server.server, "start_io", lambda: started.append(True)
        )
        lsp_server.main()
        assert started == [True]

    def test_the_server_reports_the_package_version(self):
        """A literal here had already outlived the release it named."""
        assert lsp_server.server.version == f"v{__version__}"

    def test_the_server_is_named_for_the_console_script(self):
        assert lsp_server.server.name == "acmt001-lsp"
