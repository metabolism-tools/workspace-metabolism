# Launch drafts (Show HN / r/Python)

## ACTION REQUIRED before posting: GitHub username

Account `tongflau-dongzhu` was created on 2026-05-11 (project-specific, not a
long-term personal handle), and `tongflau` is available on GitHub.

Two options:

- **A. Rename the account to `tongflau`** (cleanest). Do it in
  GitHub Account Settings (https://github.com/settings/admin). Side effects:
  both repos change URL (old links redirect automatically); the local git
  remotes of `workspace-metabolism` and the private project must be updated
  (`git remote set-url origin <new-url>`).
- **B. Keep the account, move the public repo to a neutral org**
  (e.g. `metabolism-tools`) and transfer the repo there. Private project stays
  untouched; public repo gets a clean, product-neutral owner.

Decision: PENDING (do not post until resolved).

All URLs below are placeholders and must be updated after the decision.

---

## Show HN (Hacker News)

**Recommended title**

Show HN: A policy-driven file recycler with rollback and tamper-proof audit (Python, zero-deps)

**Alternative title (more descriptive)**

Show HN: One JSON policy file controls file lifecycle: audit, recyclable clean, rollback, purge

**Body (paste into the first comment)**

`workspace-metabolism` is a zero-dependency CLI (Python 3.11+) that manages the
lifecycle of files in a workspace from a single policy file.

Why: most tools either show you disk usage (ncdu) or delete files (rmlint).
And the classic answer for "clean old files" is a cron script that calls
`rm -rf` on a path.

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

Links: [repo](<REPO_URL>) · [README](<REPO_URL>#readme) · PyPI (coming)

**Launch-day notes**

- Post Tuesday-Thursday, 09:00-12:00 US Eastern (= Beijing time 21:00-24:00)
- Answer every comment quickly; ask for edge cases they hit
- Wording on maturity: do NOT say "alpha". Say:
  "It's early days (v0.1), so the policy schema might have minor tweaks
  before v1.0. I'm looking for early adopters to break it on weird directory
  structures."

---

## r/Python

**Title**

Show /r/Python: I wrote a "safe delete" CLI that moves expired files to a recycle bin with hash-chain verification

**Body**

Long story short: my workspace kept filling up, and I wanted cleanup I could trust.

**How it works:**

- 📋 **Policy as code**: one JSON file grades paths (G1-G4)
- ♻️ **Recyclable clean**: moves to a recycle area, never `rm -rf`
- ⏪ **Rollback**: exact undo, verified with per-file SHA-256
- 🔗 **Tamper-proof audit**: hash-chained journal; `wm verify` catches changes
- ⏰ **Schedulable**: ships with cron and Windows Task Scheduler templates

It is pure stdlib (Python 3.11+), zero dependencies, and tests run on three OSes.

It's early days (v0.1), so the policy schema might have minor tweaks before v1.0. I'm looking for early adopters to break it on weird directory structures.

What would you add before trusting it with real files?

Repo: <REPO_URL>

---

## Pre-publish checklist (run before posting)

- [x] Fresh `git clone` + README quick start runs end-to-end (verified 2026-08-15)
- [x] README contains a terminal screenshot (docs/terminal-preview.png, linked in README)
- [x] `examples/registry.example.json` is valid JSON (validated)
- [ ] Username decision made (ACTION REQUIRED above)
- [ ] `<REPO_URL>` placeholders replaced with the final URL
