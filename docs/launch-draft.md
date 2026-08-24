# Launch drafts (Show HN / r/Python)

## Identity decision (resolved 2026-08-15)

The personal account stays untouched and is not referenced here. The public
tool lives under a neutral organization instead:

- Organization: `metabolism-tools`
- Final repo URL: `https://github.com/metabolism-tools/workspace-metabolism`

The private research project is not renamed, not moved, and not linked from
the public repo.

---

## Show HN (Hacker News)

**Recommended title**

Show HN: A policy-driven file recycler with rollback and tamper-proof audit (Python, zero-deps)

**Alternative title (more descriptive)**

Show HN: One JSON policy file controls file lifecycle: audit, recyclable clean, rollback, purge

**Body (paste into the first comment)**

`workspace-metabolism` is a zero-dependency CLI (Python 3.11+) that is the
**policy layer for multi-agent workspaces**: Claude Code, Codex, Aider and
OpenClaw all leave byproducts (temp files, caches, staging dirs) in the one
thing they share — your workspace — and one JSON policy file governs the
lifecycle of all of it.

Why: most tools either show you disk usage (ncdu) or delete files (rmlint).
And the classic answer for "clean old files" is a cron script that calls
`rm -rf` on a path.

I ran 30 simulated agentic loops against two identical workspaces — one with
`wm clean` after each loop, one without. The result: **2 active files vs 242**.
The governed workspace kept exactly what it needed, moved everything else to a
recyclable area, and passed hash-chain verification; the unmanaged one is a
compost pile. Reproduce it yourself:
`python examples/metabolism_benchmark.py`.

Unlike `tmpreaper`/`tmpwatch` or hand-written cron scripts that issue a real
`delete` call, **this tool never deletes during `clean`**. It moves expired
items to a recycle area and records the move with per-file SHA-256 hashes. If
you mess up, `rollback` is an exact undo; `purge` is the only command that
truly deletes, and only after retention, only inside the recycle area.

Every action lands in a hash-chained journal, and `wm verify` detects any
tampering.

Highlights:

- Policy as code: every path is graded G1-G4 (never / keep / approve + reference check / auto)
- Safety first: dry-run by default; G3 needs `--approve` + `--approver`; protected windows, size caps, reference checks
- Auditability: hash-chained journal, `wm verify` catches any edit
- Scheduling out of the box: Windows Task Scheduler + cron templates (placeholders only, no environment guessing)
- Zero dependencies; tests run on Ubuntu / Windows / macOS (Python 3.11 & 3.12)

Links: [repo](https://github.com/metabolism-tools/workspace-metabolism) · [README](https://github.com/metabolism-tools/workspace-metabolism#readme) · [PyPI](https://pypi.org/project/workspace-metabolism/)

**Launch-day notes**

- Post Tuesday-Thursday, 09:00-12:00 US Eastern (= Beijing time 21:00-24:00)
- Answer every comment quickly; ask for edge cases they hit
- Wording on maturity: do NOT say "alpha". Say:
  "It's early days (v0.2), so the policy schema might have minor tweaks
  before v1.0. I'm looking for early adopters to break it on weird directory
  structures."

---

## r/Python

**Title**

Show /r/Python: I wrote a "safe delete" CLI that moves expired files to a recycle bin with hash-chain verification

**Body**

Long story short: my workspace kept filling up — with temp files, caches and
staging dirs left behind by the agents working in it — and I wanted cleanup I
could trust.

**How it works:**

- 📋 **Policy as code**: one JSON file grades paths (G1-G4)
- ♻️ **Recyclable clean**: moves to a recycle area, never `rm -rf`
- ⏪ **Rollback**: exact undo, verified with per-file SHA-256
- 🔗 **Tamper-proof audit**: hash-chained journal; `wm verify` catches changes
- ⏰ **Schedulable**: ships with cron and Windows Task Scheduler templates

It is pure stdlib (Python 3.11+), zero dependencies, and tests run on three OSes.

The repo ships a 30-loop benchmark: two identical workspaces, one governed by
`wm clean`, one not — **2 active files vs 242**. Run it yourself in seconds.

It's early days (v0.2), so the policy schema might have minor tweaks before v1.0. I'm looking for early adopters to break it on weird directory structures.

What would you add before trusting it with real files?

Repo: https://github.com/metabolism-tools/workspace-metabolism

---

## Pre-publish checklist (run before posting)

- [x] Fresh `git clone` + README quick start runs end-to-end (verified 2026-08-15)
- [x] README contains a terminal screenshot (docs/terminal-preview.png, linked in README)
- [x] `examples/registry.example.json` is valid JSON (validated)
- [x] Identity decision made (Option B: neutral org `metabolism-tools`)
- [x] Final URLs in place (metabolism-tools/workspace-metabolism)
- [x] Org created + repo transferred (metabolism-tools/workspace-metabolism, public)
