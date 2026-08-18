Acknowledging upfront: the in-product lifecycle fix is the right endgame here — the open PR #117184 and the bot's July review already cover the lifecycle-owned candidate — and nothing I'm sharing is meant as a replacement for that work.

I'm commenting because your phrase "external scheduled cleanup is only a temporary workaround" is the exact gap I'm working on, from the outside: blind scheduled deletes vs. policy-driven governance. I maintain [workspace-metabolism](https://github.com/metabolism-tools/workspace-metabolism), a zero-dependency Python CLI where one policy file decides what each path is worth, cleanup moves items to a recycle area instead of deleting (dry-run by default), and every action lands in a hash-chained audit trail with exact `rollback`.

For the `openclaw-staged-*` residue class specifically, the read-only `audit` is a ~30-second check on a copy of a workspace — no writes unless you explicitly ask:

```bash
git clone https://github.com/metabolism-tools/workspace-metabolism.git
cd workspace-metabolism
python examples/demo.py
# or read-only on your own workspace copy:
PYTHONPATH=src python -m workspace_metabolism audit --root /path/to/copy
```

It's early days (v0.2, no external users yet), so I'm specifically looking for feedback on whether retention rules + provenance + rollback would make an external governance layer worth it for your workflow, or whether the product fix is sufficient once it lands. Either answer is useful.
