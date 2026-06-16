# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
