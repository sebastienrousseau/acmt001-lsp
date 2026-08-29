# Security Policy

## Supported versions

Security fixes are applied to the latest released version on PyPI and the
`main` branch. The table below tracks which series receive fixes.

| Version | Supported |
|---------|-----------|
| `0.0.9` | Latest released `0.0.x` only |
| < `0.0.9` | No |

A longer-term support window will be announced here once `1.0.0` ships.

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues privately by either:

1. **Preferred:** GitHub's private vulnerability reporting — open a draft
   advisory at <https://github.com/sebastienrousseau/acmt001-lsp/security/advisories/new>.
2. **Email:** `contact@sebastienrousseau.com` with the subject line
   `[acmt001-lsp security]`.

Include, where possible:

- A description of the issue and its impact (confidentiality, integrity,
  availability).
- Steps to reproduce, ideally with a minimal proof of concept.
- The affected version(s) and platform(s).
- Any suggested mitigation or fix.

## What to expect

| Stage | Target |
|-------|--------|
| Acknowledgement | Within 3 business days |
| Initial assessment | Within 10 business days |
| Fix or mitigation plan | Within 30 days for high/critical severity |
| Public disclosure | Coordinated with reporter after a fix is available |

For low-severity issues, the timeline may be longer. We will keep you updated
on progress.

## Scope

In scope:

- Code under `acmt001_lsp/` shipped to PyPI.
- The example scripts under `examples/`.
- The behaviour of the language server over its LSP transport.

Out of scope:

- Third-party dependencies (please report upstream — we will track the
  advisory and update our pinned ranges). This includes `pygls` and the
  `acmt001` library, which has its own policy.
- Vulnerabilities that require local code execution on the host already
  running the server.
- Denial-of-service via deliberately crafted input that exceeds documented
  size limits (open a feature request to add a guard instead).

## Hardening guidance for operators

A language server is not a network service, but it is still a process that
parses untrusted text:

- The server speaks LSP over stdio to its editor client. Do not expose that
  transport over a network socket without adding authentication and TLS in
  front of it; the protocol has neither.
- Documents handed to the server are parsed and validated, not executed.
  Treat account data in open buffers as PII subject to GDPR/PCI-DSS — it is
  as sensitive as the file on disk, and editor crash dumps and swap files
  can persist it.
- Keep `acmt001-lsp`, `acmt001`, `pygls`, and the Python interpreter
  patched.

## Credits

We will credit reporters who follow this policy in release notes and the
GitHub advisory, unless they request anonymity.
