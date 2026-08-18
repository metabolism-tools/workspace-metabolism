# What workspace-metabolism is not

This page answers the four most common (and most important) objections to a
tool like this. They came from real reviewers — including a sharp, public
review of this project on [anthropics/claude-code#8856](https://github.com/anthropics/claude-code/issues/8856)
(see [Provenance](#provenance)) — and they are all, in some form, correct.
Reading them before you read the feature list will tell you exactly where the
line is drawn.

## 1. Not a fix for vendor bugs

Claude Code leaving `/tmp/claude-*-cwd` files behind, OpenClaw leaving
`openclaw-staged-*` directories around, Codex and Aider caching things in odd
places — these are defects or design decisions in those products, and they
belong upstream. `workspace-metabolism` does not patch any vendor, does not
hook any agent's internals, and will never claim to "fix" Claude Code or
anyone else.

What it does instead: govern the **workspace** — the one thing every agent
shares. A policy file you own decides what each path is worth, and the tool
enforces that policy mechanically, on any machine, for any mix of agents and
tools. If a vendor fixes their bug, great: that particular residue stops
appearing. The policy layer still governs everything else that accumulates —
and agents, being agents, will keep finding new ways to accumulate.

**The line:** upstream fixes the product; `wm` governs the workspace. When
products get fixed, `wm`'s job for that specific case shrinks to nothing.
That is the best possible outcome, not a threat to the project.

## 2. Not a heuristic classifier (no guessing)

"Your script guesses what might be okay to delete by some rules" is the
fairest-sounding criticism, and it would be fatal if true. It is not:

- Nothing is classified by heuristics, machine learning, or "AI judgment".
  Every decision comes from `metabolism.json` — a policy file **you write,
  review and commit**, like source code.
- Grades are explicit (G1 never / G2 keep / G3 approve / G4 auto), and
  `wm explain <path>` shows you exactly which rule covers a path and why —
  the "nutrition label" for every file.
- Nothing happens to paths that are **not registered**. Unregistered paths
  are reported in `audit`, never touched.
- `wm audit` is read-only. `wm clean` is a dry-run unless you say `--yes`.
- The audit trail is a hash-chained journal; `wm verify` detects any edit.

The only "intelligence" in the loop is yours: you decide the policy. The tool
is a mechanical executor with a memory of everything it did.

**The line:** policy is judgment, and it belongs to the user; execution is
mechanics, and it belongs to the tool.

## 3. Not a rival to agent self-cleanup

"Agents should clean up after themselves" — yes, they absolutely should. A
session-end hook that removes its own scratchpad is the right endgame, and
`workspace-metabolism` is designed to make that endgame *safer*, not to
compete with it:

- `wm mcp` exposes a zero-dependency MCP stdio server: an agent can run its
  own micro-metabolism (audit, explain, dry-run clean plans) at the end of
  every loop — see `examples/micro_metabolism.py`.
- The policy file still decides everything; an agent hook merely triggers
  the same governed lifecycle a human would run.

If every agent cleaned up perfectly after itself, `wm` would have almost
nothing to do. That is the point of the design, not a contradiction of it.

**The line:** agent self-cleanup answers *when and where*; the policy answers
*what, how, and how to undo it*.

## 4. Not a blind-delete script

The most dangerous cleanup tool is a one-liner with a glob, because the
consequences are silent and permanent. A real example: Anthropic's own docs
once suggested a `SessionEnd` hook with `rm -f /tmp/claude-scratch-*.txt` —
a wrong path that would also delete valid, still-running sessions. The
reviewer who caught that wrote the strongest version of this objection, and
the design answers it *by construction*:

- `wm clean` never deletes by pattern. Expired items are **moved**, one
  policy entry at a time, into a recycle area — never removed in place.
- Every moved item carries per-file SHA-256 hashes; `wm rollback` verifies
  them before restoring, and refuses to overwrite anything that reappeared.
- `wm purge` is the only command that truly deletes, and it only operates
  inside the recycle area after retention, on batches recorded in the
  journal.

A wrong glob can destroy a valid session with zero trace. A wrong policy
entry can at worst recycle the wrong directory — and the journal says what,
when, and how to put it back.

**The line:** cleanup should be an event with a receipt, not a hypothesis
with a glob.

---

## The one-paragraph version

`workspace-metabolism` is the policy layer for multi-agent workspaces: it
doesn't fix agents, doesn't judge files, doesn't compete with agent
self-cleanup, and doesn't delete blindly. It lets *you* write the rules,
executes them mechanically, and keeps a hash-chained receipt for everything
— including the undo.

## Provenance

This page exists because of a public exchange on
[anthropics/claude-code#8856](https://github.com/anthropics/claude-code/issues/8856)
(2026-08-18): a reviewer pushed back on the project's first outreach comment,
pointing out that the root causes of the `/tmp/claude-*-cwd` leak are upstream
(system-prompt scratchpad placement, missing cleanup directives, missing
close hooks), that residue on tmpfs costs RAM rather than disk, and that a
rule-based cleanup tool "looks like it tries to guess what might be okay to
be deleted". All four points are addressed here in order. The exchange is
kept on record so the project's positioning stays honest as it grows.
