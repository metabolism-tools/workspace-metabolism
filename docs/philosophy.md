# Metabolism Engineering: a philosophy for AI workspaces

Status: proposal, 2026-08-15. This document proposes a framing — it does not
claim to have coined the words. The biological metaphor has precedents (for
example "information metabolism", Kepiński, 1960s), and the term "metabolic
engineering" belongs to synthetic biology. What is proposed here is applying
that metaphor to the **file lifecycle of AI-assisted workspaces**, and the
proposal is embodied by the `workspace-metabolism` tool.

## 1. The problem: AI workspaces accumulate byproducts

Vibe coding and agentic loops have changed what a workspace looks like:

1. AI generates code
2. something errors
3. AI fixes it
4. a new dependency or script appears
5. a previous approach is abandoned, but not removed
6. the cycle repeats

The result: `archive/`, `deprecated/`, `test_drafts/`, `tmp/`, half-finished
refactors and duplicated lock files grow **faster than the code itself**. The
workspace becomes a compost pile without a gardener.

## 2. Why "just delete it" is not enough

The classic answer is a cleanup script that calls `rm -rf`. That is
**autophagy**: it burns potentially valuable intermediate matter. An AI's next
loop might need the very file that was just destroyed, and once it is gone the
provenance is gone with it.

The other extreme is pure git. Git is right for tracked source, but most
workspace byproducts are untracked, high-churn, non-code assets: caches, logs,
draft outputs, one-off experiments. Versioning every one of them is too heavy.

## 3. The four phases

Metabolism Engineering is not "delete garbage". It is a digestion system for
the workspace, defined by four phases that map directly to `wm` commands:

| Phase | Tool | What it means in an AI workspace |
| --- | --- | --- |
| **Catabolism** | `wm audit` | Digestive diagnosis: scan the workspace and label candidates — abandoned blueprints, duplicate lock files, stuck half-products. It does not judge; it adds a nutrition label. |
| **Sequestration** | `wm clean` | Gentle fermentation: move confirmed-expired matter into the recycle area. Never `rm -rf`, because the next agent loop might need a file that looks dead. |
| **Verification** | `wm verify` | Bioassay: the hash-chained journal records when matter was produced and when it moved. Any tampering is detected. |
| **Anabolism** | `wm rollback` | Reabsorption: when a new loop discovers the old approach was better after all, rollback re-injects the material into the active workspace. Waste becomes feedstock. |

## 4. Where this fits: Harness, Loop, Metabolism

- **Harness Engineering** designs the runtime environment that constrains an
  agent.
- **Loop Engineering** designs the plan → execute → observe → reflect cycle.
- **Metabolism Engineering** answers what happens to the byproducts each loop
  leaves behind — the last mile of every loop.

Proposal: at the end of each loop (after observation, before the next plan), a
**micro-metabolism** step asks: "The files just produced — keep, archive,
recycle, or leave for tomorrow's digestion?" The tool's scheduled `audit`
(daily) and `clean` (weekly) are the mechanical form of that question.

## 5. How this differs from existing cleanup tools

| | tmpreaper / tmpwatch | AI-cleanup tools (zclean, agent-gc, vanish…) | workspace-metabolism |
| --- | --- | --- | --- |
| Policy file governs everything | no | no | **yes** |
| Deletes directly | yes | often | **never during clean** |
| Recycle + exact rollback | no | no | **yes** |
| Tamper-proof hash-chain audit | no | no | **yes** |
| Scheduled dual-OS runs | partial | no | **yes** |
| Zero dependencies | yes | varies | **yes** |

Cleanup tools answer "what should be deleted". This project answers "what
should be kept, recycled, or reactivated" — and makes that answer auditable.

## 6. FAQ

**"Isn't this just cleanup?"**

Cleanup is the means; metabolism is the frame. Cleanup optimizes for "less
stuff"; metabolism optimizes for "the right stuff at the right time, with a
verifiable history". The difference shows in the safety model: nothing is
destroyed without a recoverable, verified move.

**"Isn't this just tmpreaper with a rebrand?"**

The lifecycle model is the difference: policy-as-code grades (G1–G4),
recyclable cleanup with per-file SHA-256, hash-chained journal verification,
and rollback. tmpreaper's answer to "I deleted something I needed" is "sorry";
this tool's answer is `wm rollback <run_id>`.

**"Why not just use git?"**

Git versions tracked source. Workspace byproducts are mostly untracked,
high-churn and non-code. This tool governs them without forcing a commit
discipline onto every temporary file.

**"Is 'Metabolism Engineering' an original term?"**

Honest answer: the metaphor is not new ("information metabolism" dates to the
1960s; "metabolic engineering" is an established bioengineering discipline).
What this project proposes is applying the metaphor to AI workspace lifecycle
governance, and giving it a concrete, auditable tool. We claim the framing, not
the words.

## 7. Relationship to this repository

This document is the philosophy; the tool is the practice. The repository is
MIT-licensed so the framing and the implementation can be reused, criticized
and improved independently.
