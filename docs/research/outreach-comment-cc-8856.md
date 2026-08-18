To be clear up front: this is not a fix for Claude Code itself — the leak needs an upstream fix, and I can see this thread is already trying plugin-based mitigations. I'm sharing an independent tool because the `/tmp/claude-*-cwd` flood is one instance of a broader problem I'm working on: agent workspaces accumulating byproducts with no policy and no undo.

[workspace-metabolism](https://github.com/metabolism-tools/workspace-metabolism) is a zero-dependency Python CLI where one policy file (`metabolism.json`) decides what each path is worth, and nothing is ever deleted directly:

- `wm audit` — read-only report: candidates, unregistered paths, growth trend
- `wm clean --grades G4` — moves expired items to a recycle area (dry-run by default)
- `wm rollback <run_id>` — restores a run after a per-file SHA-256 integrity check
- every action lands in a hash-chained journal; `wm verify` detects edits

It's early days (v0.2, no external users yet), so I'm looking for people to run it against real clutter. 30-second throwaway trial, nothing touches your real machine:

```bash
git clone https://github.com/metabolism-tools/workspace-metabolism.git
cd workspace-metabolism
python examples/demo.py
# read-only audit on a copy of your own workspace:
PYTHONPATH=src python -m workspace_metabolism audit --root /path/to/copy
```

Genuinely curious: for the 174-files-a-day case, would an "audit → recycle → rollback" workflow be more useful than a plain cleanup script — or is a delete-on-exit hook all you actually need?
