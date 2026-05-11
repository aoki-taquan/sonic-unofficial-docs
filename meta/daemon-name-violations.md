# Daemon Name Verification — Violations

Scanned `docs/**/*.md`, extracted 91 unique daemon-like tokens matching `*cfgd|*mgrd|*syncd|*orch|*orchd`, and grep-verified each against `.cache/sonic-sources/`.

- Verified token count: **91**
- Violations (not found in master sources): **0**

No violations: every daemon-like token resolves to a master source file.

