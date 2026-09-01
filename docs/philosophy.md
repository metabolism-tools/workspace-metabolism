# Agentic Metabolic Engineering: a philosophy for agent-driven workspaces

Status: proposal, 2026-08-15. This is a framing, not a claim of novelty. The
metaphor has precedents in biology and systems thinking; here it is used only
to describe a workspace lifecycle.

**Agentic Metabolic Engineering** is the method for thinking about workspace
lifecycle in agent-driven software workspaces. It decides what should stay,
what should be recycled, and what can be restored later. The implementation is
`workspace-metabolism`.

`AI governance as code` is the practical form of that method inside this repo:
policy files, commands, and recorded decisions.

Short handle: **Workspace Metabolism**.
One-liner: **Loops keep the agent running; metabolism keeps the workspace usable.**

## 1. The problem

Agentic loops make workspaces grow in a specific way:

1. the agent writes code
2. it tries a fix
3. a draft, cache, or script appears
4. the old attempt is left behind
5. the next loop has to work around the residue

The result is familiar: `archive/`, `deprecated/`, `test_drafts/`, `tmp/`,
half-finished refactors, and duplicate lock files accumulate faster than the
useful code. The workspace stops feeling like a working surface and starts
feeling like a pile of leftovers.

## 2. Why not just delete it

The usual answer is a cleanup script that calls `rm -rf`. That is fast, but it
destroys intermediate material the next loop may still need, and it erases
provenance at the same time.

The other extreme is pure git. Git is right for tracked source, but most
workspace byproducts are untracked, high-churn, non-code assets: caches, logs,
draft outputs, one-off experiments. Putting all of that into version control is
too heavy.

## 3. The four phases

Agentic Metabolic Engineering is a workspace lifecycle model with four phases
that map directly to `wm` commands:

| Phase | Tool | What it means |
| --- | --- | --- |
| **Catabolism** | `wm audit` | Scan and label the workspace so the next decision is based on evidence, not guesswork. |
| **Sequestration** | `wm clean` | Move confirmed-expired matter into the recycle area instead of deleting it in place. |
| **Verification** | `wm verify` | Check the hash-chained journal so changes stay auditable and tamper-evident. |
| **Anabolism** | `wm rollback` | Restore a recycled item when a later loop needs it again. |

## 4. Where it fits

One useful way to see the field is as a layered engineering stack for agentic
AI:

| Layer | Paradigm | Core question |
| --- | --- | --- |
| L1 | Prompt Engineering | What do we say to the model? |
| L2 | Context Engineering | What do we give the model to read? |
| L3 | Harness Engineering | How do we make the agent reliable in production? |
| L4 | Loop Engineering | How does the agent run itself without us? |
| L5 | Agentic Metabolic Engineering | What happens to the byproducts after each loop? |

Each layer removes a different kind of manual work. Prompt handles the words,
Context handles the information, Harness handles runtime constraints, and Loop
handles orchestration. Agentic Metabolic Engineering handles the workspace
itself: it treats capacity as finite, and it manages the files left behind
instead of assuming they will disappear on their own.

Without metabolism, a loop keeps producing residue until the workspace slows
down. With it, the workspace stays recoverable and reusable instead of slowly
clogging itself.

## 5. Micro-metabolism

At the end of each loop, after observation and before the next plan, a
micro-metabolism step asks a simple question: what should be kept, what should
be recycled, and what should be left for later?

In practice, this can be a wrapper around `wm audit --json` that an agent
calls before the next planning phase. Scheduled `audit` and `clean` runs are
the unattended version of the same question.

The human role shifts accordingly: not janitor, but **policy author** - the
person who decides what every path is worth (G1-G4), how long byproducts rest,
and which items can be restored later.

## 6. How it differs from cleanup tools

| | tmpreaper / tmpwatch | AI-cleanup tools (zclean, agent-gc, vanish) | workspace-metabolism |
| --- | --- | --- | --- |
| Policy file governs everything | no | no | yes |
| Deletes directly | yes | often | never during `clean` |
| Recycle + exact rollback | no | no | yes |
| Tamper-proof hash-chain audit | no | no | yes |
| Scheduled dual-OS runs | partial | no | yes |
| Zero dependencies | yes | varies | yes |

Cleanup tools answer "what should be deleted". This project answers "what
should be kept, recycled, or reactivated" and makes that answer auditable.

### 6.1 Adjacent tools

The table above groups zclean, agent-gc, and vanish together; they deserve
separate mention because each solves a real but different problem. The
comparison below is about the lifecycle model, not a judgement of the tools.

| | zclean | agent-gc | vanish | workspace-metabolism |
| --- | --- | --- | --- | --- |
| Package | npm `@thestackai/zclean` | Rust / npm `agent-gc` | PyPI `vanish` | PyPI `workspace-metabolism` |
| Main target | zombie/orphaned agent processes, MCP servers, dev caches | agent worktrees, duplicate dependencies, build artifacts | venv / node_modules / build caches across the home directory | any registered path in an AI-driven workspace |
| Deletion model | deletes after dry-run + `--yes` | deletes | deletes | never during `clean`; recycle area, then `rollback` |
| Policy file grades paths (G1-G4) | no | no | no | yes |
| Recycle + exact rollback | no | no | no | yes |
| Hash-chain audit + `verify` | no | no | no | yes |
| Zero dependencies | yes (Node) | n/a (Rust) | n/a | yes (Python stdlib) |

Based on public package descriptions and READMEs as of 2026-08-17; verify
current details before quoting them. Caveat: `vanish` (PyPI) could not be
independently verified during the 2026-08 competitive research sweep, so that
row reflects its self-description only.

## 7. What this is not

- Not a vendor fix. It governs the workspace, not the agent internals.
- Not a heuristic classifier. Decisions come from `metabolism.json`.
- Not a rival to agent self-cleanup. It can support that workflow.
- Not a blind-delete script. `clean` moves items first; `purge` is the only
  real delete, and only inside the recycle area.

## 8. Relationship to this repository

This document is the philosophy; the tool is the practice. The repository is
MIT-licensed so the framing and the implementation can be reused, criticized,
and improved independently.

If you disagree with the framing, or if you have a better metaphor, open an
Issue. The goal is not to win the metaphor; it is to make workspace lifecycle
governance concrete, honest, and usable.
