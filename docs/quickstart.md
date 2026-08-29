# Quickstart

Install → editor wiring → first account-data edit, for `acmt001-lsp`.

## 1. Install

`acmt001-lsp` runs on macOS, Linux, and Windows and requires Python
3.10+. It pulls in the core `acmt001` library and `pygls` automatically.

```sh
python -m pip install acmt001-lsp
```

Verify:

```sh
python -c "import acmt001_lsp; print(acmt001_lsp.__version__)"
```

## 2. Confirm the server starts

```sh
acmt001-lsp
```

Nothing visible happens — the command speaks LSP on stdin/stdout. Press
Ctrl-C to exit. It is meant to be launched by your editor, not used
interactively.

## 3. Wire it up

### Neovim (built-in `vim.lsp.config`)

```lua
vim.lsp.config["acmt001"] = {
  cmd = { "acmt001-lsp" },
  filetypes = { "json" },
  root_markers = { ".git" },
}
vim.lsp.enable("acmt001")
```

### VS Code

Use a generic LSP client extension and point its `serverOptions` at
`{ command: "acmt001-lsp", transport: stdio }`, with a document selector
for `json`.

## 4. What you get

Open a JSON file holding a list of account-management records:

```json
[
  {
    "msg_id": "ACMT-MSG-0001",
    "creation_date_time": "2026-01-15T10:30:00",
    "account_id": "GB29NWBK60161331926819",
    "account_currency": "EUR",
    "account_servicer_bic": "NWBKGB2LXXX",
    "account_owner_name": "Acme Embedded Finance Ltd",
    "account_owner_country": "GB"
  }
]
```

Three features are live:

- **Diagnostics** on open and on every change. Records are validated
  against the message-type schema, and any identifier fields present
  (IBAN, BIC, LEI) are checked individually.
- **Completion** offers every input field for the message type, with its
  schema description as the detail, plus every supported message type.
- **Hover** over a field name shows that field's schema description.

The server validates against `acmt.007.001.05` (Account Opening Request)
by default. `compute_diagnostics`, `completion_items` and `hover_text`
each take a `message_type` argument if you are driving them directly.

## 5. Editing feels how?

A single record is validated in a couple of milliseconds — well inside
one frame, so squiggles track the cursor. Cost grows with record count
because each record is validated independently: see
[benchmarks.md](benchmarks.md) for measured numbers and where the
responsiveness thresholds sit.

While you are mid-edit — a quote not yet closed — JSON parsing fails
immediately and no record is validated, so the state the editor calls
most often is also the cheapest.
