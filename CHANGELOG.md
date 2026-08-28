# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.2] - 2026-08-28

The first release since 0.0.1, and the one that brings this package up to
the rest of the suite's testing standard.

### Changed

- **The `acmt001` floor moves to `>=0.0.5`,** from `>=0.0.1`. 0.0.5 is
  the first release built against `xmlschema >=4.3.2`. Anything lower
  admits 0.0.4, which pins `xmlschema<4.0.0` and cannot be installed
  beside `pain001` or `camt053`. A resolver that lands there reports
  `ResolutionImpossible` without naming the cause.

- **The server reports the package version instead of a literal.** It
  announced itself as `v0.0.1` from a hardcoded string, which had
  already outlived the release it named. An editor showing a stale
  server version is a confusing thing to debug.

### Added

- **A coverage gate at 100%,** with branch coverage. There was none, and
  the module sat at **73%** — the outlier in a suite where everything
  else is at 98 or above.

- **`tests/test_lsp_glue.py`,** covering what the 73% left out: all four
  `@server.feature` handlers, the mapping to `lsprotocol` types, `main`,
  and the line-offset heuristic underneath every diagnostic.

  The heuristic was the part worth testing. It finds each record by
  tracking top-level `{`, and a brace inside a string or a nested object
  must not be mistaken for one — get that wrong and every subsequent
  squiggle lands on the wrong record, silently, with nothing raised. Two
  of the new assertions were mutation-tested against exactly that:
  removing the escape-handling branch, and inverting the unknown-severity
  fallback, each fail the test written for them.

## [0.0.1] - 2026-06-16

### Added

- Initial release of `acmt001-lsp`, a [pygls](https://github.com/openlawlibrary/pygls)-based
  Language Server Protocol (LSP) server for authoring acmt001 account-data
  JSON files (Python 3.10+)
- An `acmt001-lsp` console entry point that starts the language server over
  stdio for editor LSP clients
- **Diagnostics** — schema validation of each record against a message
  type's input JSON Schema (missing required fields, types, patterns) plus
  IBAN / BIC / LEI validation of identifier fields
- **Completion** — every input field (with its schema description) and the
  full list of supported acmt message types
- **Hover** — schema descriptions for the field under the cursor
- Pure, importable helper functions (`compute_diagnostics`,
  `completion_items`, `hover_text`) backed by the shared `acmt001.services`
  layer, so editor behaviour matches the CLI, REST API, and MCP server
- Part of the **acmt001 suite** alongside the core `acmt001` library and the
  `acmt001-mcp` Model Context Protocol server

[0.0.1]: https://github.com/sebastienrousseau/acmt001-lsp/releases/tag/v0.0.1
