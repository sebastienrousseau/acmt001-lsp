# acmt001-lsp

A [pygls](https://github.com/openlawlibrary/pygls)-based
[Language Server](https://microsoft.github.io/language-server-protocol/) for
authoring [`acmt001`](https://github.com/sebastienrousseau/acmt001) account-data
JSON files — real-time diagnostics, completion, and hover in your editor.

Part of the **acmt001 suite**: [`acmt001`](https://pypi.org/project/acmt001/)
(core) · [`acmt001-mcp`](https://pypi.org/project/acmt001-mcp/) ·
`acmt001-lsp` (this package).

## Install

Requires **Python 3.10+** (it pulls in `acmt001` and `pygls`):

```sh
python -m pip install acmt001-lsp
```

## Run

Launch the server over stdio and point your editor's LSP client at it for JSON
account files:

```sh
acmt001-lsp
```

## Features

For account-data JSON files (a JSON array of flat account records):

- **Diagnostics** — missing required fields and invalid IBAN/BIC/LEI values.
- **Completion** — field names and message types from the input schema.
- **Hover** — field descriptions from the input schema.

The feature logic lives in pure, importable helpers (`compute_diagnostics`,
`completion_items`, `hover_text`) backed by the shared `acmt001.services` layer.

## Licence

Apache-2.0.
