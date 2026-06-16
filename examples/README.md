# acmt001-lsp examples

Runnable, self-contained examples for the **acmt001-lsp** language server. Run
any of them from the repository root:

```sh
python examples/<name>.py
```

| Example | Demonstrates |
|---------|--------------|
| [`lsp_helpers.py`](lsp_helpers.py) | The LSP diagnostics / completion / hover helpers (`compute_diagnostics`, `completion_items`, `hover_text`) |

These helpers are exactly what the `acmt001-lsp` server runs on each edit, so
you can call them directly to see the diagnostics, completion items, and hover
text an editor would receive.

Both `acmt001-lsp` and its core dependency `acmt001` must be installed
(Python 3.10+):

```sh
pip install acmt001-lsp
```
