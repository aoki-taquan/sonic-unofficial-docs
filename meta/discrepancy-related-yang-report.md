# `verification: discrepancy-found` pages with empty `related.yang`

Informational lint — discrepancy-found pages typically reference
YANG modules in the body. Leaving `related.yang` empty hides those
back-refs from the related-pages sidebar.

- scanned: 832
- discrepancy-found total: 62
- empty `related.yang`: 9
- opted out (`_no_related: true`): 2

## Violations

- `docs/architecture/error-handling-framework-in-sonic-operations.md`
- `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-concepts.md`
- `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md`
- `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md`
- `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-operations.md`
- `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md`
- `docs/platform/liquid-cooling-leakage-detection-in-sonic.md`
- `docs/platform/smartswitch-dpu-graceful-shutdown.md`
- `docs/system/sonic-python-logger-enhancement.md`

## Opted-out

- `docs/architecture/build-profiles.md`
- `docs/system/hld-secure-boot.md`
