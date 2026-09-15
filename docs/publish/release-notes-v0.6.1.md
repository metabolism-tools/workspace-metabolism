# v0.6.1: Triageable Audit Output

This release makes the model-facing audit result proportional to what it finds.
It does not add a scheduler, a policy field, an AI runtime, or a Symphony
integration.

## Included

- `wm_audit` gains `detail: "summary" | "full"`, default `summary`. Summary
  returns sensitive files as counts plus one group per dependency tree
  (`site-packages/`, `dist-packages/`, `node_modules/`) and lists
  workspace-owned files individually; `full` returns every entry, as 0.6.0 did.
- New `core.summarize_sensitive()`: groups are ordered by count, so the biggest
  tree is read first, and a vendored tree that does not use a marker directory
  stays visible as workspace-owned — over-reporting, never hiding.
- Nothing is dropped in either mode. The complete list is still written to the
  audit report file, `summary.sensitive` still carries the count, and the
  report path now travels with the payload as `report_path`.
- `docs/dsh-integration.md` records the new default for the DSH bridge.

Measured on a real agent workspace (88,377 files, 1,294 MB, 411 sensitive hits),
same call, same run:

| mode | payload |
| --- | --- |
| `detail="summary"` (new default) | 3.7 KB |
| `detail="full"` (0.6.0 behaviour) | 74.9 KB |

402 of those 411 entries were third-party package filenames inside nested
virtualenvs, and the actionable maintenance content of the call was zero.

## Installation

GitHub release assets include a wheel and source archive:

```console
python -m pip install https://github.com/metabolism-tools/workspace-metabolism/releases/download/v0.6.1/workspace_metabolism-0.6.1-py3-none-any.whl
wm --version
```

PyPI remains a separate publishing channel, as noted in the 0.6.0 release: do
not expect an ordinary `pip install --upgrade workspace-metabolism` to install
0.6.1 until its PyPI publication is confirmed.

## Compatibility and Limits

- **The default `wm_audit` payload no longer inlines the full sensitive list.**
  A caller that parsed `sensitive` as a list must pass `detail: "full"`. The key
  keeps one type per mode, and the count in `summary.sensitive` is unchanged.
- Classification is by path only. A dependency tree without a marker directory
  is reported as workspace-owned.
- No change to dry-run defaults, approval gates, verified rollback, the journal,
  or any cleanup decision. The sensitive list remains advisory and never
  authorizes cleanup on its own.
- Also in this release: `test_protected_window_blocks_when_active` and
  `test_protected_window_skips_weekend` were failing on main once real time
  moved past their hardcoded `now` (the fixture aged against wall-clock time).
  The fixture is now stamped against the test's own clock; assertions are
  unchanged.

## Verification

- Local full package regression: 375 passed, 1 skipped (Windows symlink fixture
  unavailable).
- CI on the change pull request: 14 checks, all passing (Python 3.11/3.12 on
  Windows, Linux and macOS, plus CodeQL).
- The release checkout is based on current upstream main, not the older
  development checkout.
- Package build/install and a clean-environment `wm --version` and `wm_audit`
  check are performed before the release tag.
