# Contributing

Thanks for considering a contribution. This project is small on purpose: a
zero-dependency CLI whose core promise is "the tool only ever does what the
policy allows, and every action is verifiable."

## Ground rules

- **Never break the safety model.** `clean` must stay dry-run by default,
  `rollback` must verify hashes and refuse to overwrite, `purge` must stay the
  only real delete, and the journal must detect tampering. Changes touching
  these paths need explicit review.
- **Zero runtime dependencies.** Anything you need beyond the Python standard
  library must live behind an optional integration (like the MCP server,
  which is stdlib-only).
- **Evidence over claims.** Docs and narratives may propose ideas; the code
  must prove them. New claims in docs should point to tests or the benchmark.

## Development setup

```bash
python -m pip install -e . pytest
python -m pytest
```

The test suite covers core, CLI, and the MCP server. Keep it green on
Windows, Linux and macOS (CI runs all three with Python 3.11 and 3.12).

## Making a change

1. Open an Issue first for anything that changes behavior or the policy
   schema. Small doc fixes and tests can go straight to a PR.
2. Add or update tests alongside the change.
3. Run the full suite and include the result in the PR description.
4. Keep the narrative honest: if a feature changes what the tool can do,
   update the relevant docs (README, philosophy, narrative) in the same PR.

## Review checklist

- [ ] `python -m pytest -q` passes
- [ ] New CLI flags/commands are documented in README
- [ ] Policy schema changes update `schema/metabolism.schema.json`
- [ ] No new runtime dependencies
- [ ] Fail-closed guarantees still hold (dry-run defaults, approval gates,
      verified rollback, tamper-proof journal)
