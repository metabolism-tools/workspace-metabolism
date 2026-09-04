The fork PR above (and #36428's cleanup-on-exit) is the right endgame — I won't argue that a fix isn't the real answer, and nothing I'm sharing is meant as a replacement for that work.

I'm commenting because the *project-root* part of this is the exact gap I work on from the outside: the working directory is the one thing every tool and every future agent session shares, and once `Q*.tmp` files land there, nothing in the workspace distinguishes them from real work. I maintain [workspace-metabolism](https://github.com/metabolism-tools/workspace-metabolism), a zero-dependency Python CLI where one policy file decides what each path is worth; cleanup moves items to a recycle area instead of deleting (dry-run by default), and every action lands in a hash-chained journal with exact `rollback`.

For the 100+ files already in the project root, the read-only `audit` is a ~30-second check on a copy of a workspace — no writes unless you explicitly ask:

```bash
git clone https://github.com/metabolism-tools/workspace-metabolism.git
cd workspace-metabolism
python examples/demo.py
# or read-only on your own workspace copy — the --root flag is a global option since v0.3,
# and audit expects a metabolism.json policy in the target dir:
PYTHONPATH=src python -m workspace_metabolism --root /path/to/copy init   # once per copy
PYTHONPATH=src python -m workspace_metabolism --root /path/to/copy audit
```

It's early days (v0.2, no external users yet), so I'm specifically looking for feedback on whether audit → recycle → rollback is a useful middle step for residue that's *already accumulated* and unreferenced, or whether a plain delete-all is the only honest answer until the upstream fix ships. Either answer is useful.
