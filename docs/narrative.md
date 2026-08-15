# Agentic Metabolic Engineering: a narrative

Status: proposal, 2026-08-15. This document tells the story; the definitions
live in [philosophy.md](philosophy.md). It is written to be usable as a blog
post, a Show HN companion, or a conference talk outline.

Honest framing, restated once: we propose this framing, we do not claim to
have coined the words. The metaphor has precedents ("information metabolism",
Kepiński, 1960s) and "metabolic engineering" is an established bioengineering
discipline.

## 1. The origin

Vibe coding and agentic loops changed what a workspace looks like:

1. AI generates code
2. something errors
3. AI fixes it
4. a new dependency or script appears
5. a previous approach is abandoned, but not removed

The result is a workspace that accumulates drafts, caches, failed attempts and
half-finished refactors faster than the code grows. Left alone, it becomes a
compost pile without a gardener — and the next loop has to work inside it.

**Agentic Metabolic Engineering** is the engineering paradigm for managing the
lifecycle of those byproducts: classify, isolate, verify, and reabsorb — with a
policy file as the source of truth and an audit trail that cannot be silently
rewritten.

## 2. The stack

One useful way to see the field is as a layered engineering stack for agentic
AI:

| Layer | Paradigm | Core question |
| --- | --- | --- |
| L1 | Prompt Engineering | What do we say to the model? |
| L2 | Context Engineering | What do we give the model to read? |
| L3 | Harness Engineering | How do we make the agent reliable in production? |
| L4 | Loop Engineering | How does the agent run itself without us? |
| L5 | Agentic Metabolic Engineering | What happens to the byproducts after each loop? |

Each layer abstracts away a piece of human labor: Prompt abstracts the words,
Context the information, Harness the runtime constraints, Loop the
orchestration. Agentic Metabolic Engineering abstracts the **workspace
itself** — treating it not as an infinite sandbox, but as a living system with
limited capacity that needs digestion, not just deletion.

## 3. The method

### The four phases

| Phase | Command | What it does |
| --- | --- | --- |
| Catabolism | `wm audit` | Scan and label: abandoned drafts, duplicate caches, half-finished refactors. Diagnosis without destruction. |
| Sequestration | `wm clean` | Move confirmed-expired matter to a recycle area. Never `rm -rf` — the next loop might need what looks dead today. |
| Verification | `wm verify` | Check the hash-chained journal: when each file was produced and when it moved. Tampering is detected. |
| Anabolism | `wm rollback` | When a new loop discovers the old approach was better, re-inject the material into the active workspace. Waste becomes feedstock. |

### Policy as code

Every path is graded G1–G4 in one JSON policy file (never / keep /
approve + reference check / auto). The tool only ever does what the policy
allows — nothing more, nothing automatic.

### Micro-metabolism

At the end of each loop (after observation, before the next plan), a
micro-metabolism step asks: "The files just produced — keep, archive, recycle,
or leave for tomorrow's digestion?" In practice this can be a wrapper script
around `wm audit --json` that an agent calls before its next planning phase,
making the tool a native part of the loop's observation step. Scheduled daily
`audit` and weekly `clean` runs are the unattended form of the same question.

### The anti-patterns

- **Autocracy**: a cron script that `rm -rf`s a path. It burns intermediate
  matter that a future loop might need, and with it the provenance.
- **Hoarding**: never clean anything. The workspace rots, the agent's context
  gets contaminated, and every loop gets slower.
- **Clean-slate**: rebuild a fresh sandbox every loop. Expensive, and it throws
  away exactly the history that makes iteration possible.
- **Gold-plated git**: commit every byproduct. The version history becomes a
  landfill and nobody can find anything.

## 4. The debt

**Metabolic Debt** is the cost of unmanaged workspace byproducts — the
accumulating drag that agent loops pay as files pile up, context gets
contaminated, and old implementations collide with new ones. It is to a
workspace what technical debt is to a codebase.

If technical debt has budgets and repayment rituals, metabolic debt should
too:

| Metabolic debt concept | Tool counterpart |
| --- | --- |
| Debt checkup | `wm audit` — sizes the workspace, lists candidates, flags disk alerts |
| Debt tiers | G1–G4 grades — what must never be touched vs what is safe to recycle |
| Debt deferral | The recycle area — nothing is destroyed until retention expires |
| Debt repayment | `wm rollback` — reabsorbing a file a new loop turns out to need |

**Workspace Rot** is the failure mode of unpaid metabolic debt: a workspace so
cluttered that agent performance and reliability measurably degrade. The
opposite of rot is not emptiness — it is *rightness*: the right files, at the
right time, with a verifiable history.

### Vocabulary: paradigm terms vs tool terms

- **Paradigm terms** (anyone may use): `Metabolic Debt`, `Workspace Rot`.
  These are open concepts — the goal is for the ecosystem to adopt them, not
  for one tool to own them.
- **Tool terms** (specific to this implementation): `micro-metabolism`,
  `digestion without deletion`. These describe how `workspace-metabolism`
  realizes the paradigm.

## 5. The measure

A paradigm is only as good as its ability to be measured. Four metric groups
cover the lifecycle:

| Metric group | Indicator | Where it appears |
| --- | --- | --- |
| Growth | workspace size and files, growth since last audit | `audit` summary |
| Recycle | files and MB in the recycle area, ratio to workspace | `audit` summary, `status` |
| Auditability | journal entries, hash chain integrity | `audit` summary, `verify` |
| Governance | G3 vs G4 candidates, unregistered paths, disk alerts | `audit` summary, report |

`wm audit --json` outputs a `summary` block with these fields today:

```json
{
  "files": 2,
  "size_mb": 0.0,
  "growth_mb": null,
  "candidates": 2,
  "candidates_g4_mb": 0.0,
  "candidates_g3_mb": 0.0,
  "unregistered": 0,
  "disk_alert": false,
  "recycle_files": 0,
  "recycle_mb": 0.0,
  "recycle_ratio_pct": 0.0,
  "journal_entries": 1,
  "journal_chain_ok": true
}
```

So the measurement ritual is a one-liner:

```bash
wm audit --json | jq '.summary.growth_mb, .summary.recycle_ratio_pct, .summary.journal_chain_ok'
```

Notes: `growth_mb` is `null` on the first audit (no baseline yet); the recycle
ratio becomes meaningful after the first `clean`. On Windows, replace `jq`
with `python -m json.tool` or read the fields directly from the report.

## 6. The roadmap

- **Today**: CLI + policy file + scheduled runs (Windows Task Scheduler, cron)
- **Near term**: agent-native integration — `wm audit --json` is the first
  contract; an MCP server that lets agents run micro-metabolism themselves is
  the next step
- **Mid term**: a workspace health score that combines the four metric groups
  into one number
- **Far term**: metabolism policy as a standard project artifact, as common as
  `.gitignore`

`workspace-metabolism` is the reference implementation, not the standard. The
paradigm is bigger than the tool.

## 7. The invitation

We propose **Agentic Metabolic Engineering** as a framing — the fifth layer of
the agentic stack, and the last mile of every loop. It is not a claim of
coining, and it is not finished.

If you disagree with the framing, or have a better metaphor, open an Issue.
The goal is not to be right, but to start a conversation about what happens to
the byproducts of our new coding habits — and to give the workspace a digestion
system instead of a funeral pyre.
