# Agents loop; workspaces must metabolize

*A short essay on Agentic Metabolic Engineering, the fifth layer of the
agentic stack. English, ~900 words. Suitable for dev.to, a personal blog, or
the Hacker News follow-up after Show HN.*

---

Prompt engineering taught us what to say to a model. Context engineering
taught us what to let it read. Harness engineering built the runtime that
keeps an agent reliable, and loop engineering designed the cycles that let it
run without us. Each of these layers was a real shift: the object of our
engineering moved one step further from the model and one step closer to the
system around it.

There is one more step in that direction, and it is the one nobody is
managing yet: what happens to the workspace after each loop.

## The fountain without a drain

AI writes code like a fountain. Most workspaces have no drain.

An agent loop looks innocent on the surface: generate, error, fix, repeat.
But every repetition leaves a trace -- a draft, a patch, a lock file, a test
stub, a half-finished refactor, an abandoned approach that was never deleted.
Code grows; the workspace grows faster. Left alone, the project becomes a
compost pile without a gardener, and the next loop has to work inside its own
mess. Context gets contaminated. Builds slow down. Old implementations collide
with new ones. The cost is not disk space; it is the reliability of every
future loop.

The classic answer is a cron script that calls `rm -rf`. That is autophagy: it
burns intermediate matter a future loop might need, along with its
provenance. The opposite extreme -- commit everything to git -- turns version
history into a landfill. And rebuilding a fresh sandbox every loop throws away
exactly the history that makes iteration possible.

## The third act

The story so far has two acts. In the first, prompt engineering made the AI
able to write. In the second, harness and loop engineering made it able to
keep writing -- reliably, autonomously, for hours. That autonomy is precisely
what creates the new problem: an agent that runs for hours leaves hours of
byproducts behind.

The third act is about whether the workspace can survive the writing.

We propose calling it **Agentic Metabolic Engineering**: the fifth layer of
the agentic stack, and the last mile of every loop. The one-liner is:

> Loops keep the agent running; metabolism keeps the workspace alive.

## Four phases, one policy file

Metabolism, applied to a workspace, has four phases that map directly to
commands:

| Phase | Command | Meaning |
| --- | --- | --- |
| Catabolism | `wm audit` | Read-only diagnosis. Label candidates; judge nothing. |
| Sequestration | `wm clean` | Move expired matter to a recycle area. Never delete directly. |
| Verification | `wm verify` | Check the hash-chained journal. Tampering is detected. |
| Anabolism | `wm rollback` | Re-inject recycled matter when a new loop needs it. Waste becomes feedstock. |

Everything is governed by one JSON policy file that grades every path
G1-G4 (never / keep / approve + reference check / auto). The tool only ever
does what the policy allows. Deletion is never direct: items move to a recycle
area, `rollback` restores them after per-file SHA-256 checks, and `purge` is
the only real delete, gated by retention and restricted to the recycle area.

The human role shifts accordingly: not janitor, but **policy author** -- the
person who decides what every path is worth, how long byproducts rest, and who
must approve G3 recycling. The tool enforces the policy; the person designs
the metabolism.

## The measurement

A paradigm is only as good as its ability to be shown. The reference
implementation ships a reproducible experiment: two identical workspaces run
30 simulated agent loops, each leaving eight byproduct files. One workspace
ends every loop with a policy-driven clean; the other simply accumulates.

After 30 loops:

| | Governed | Ungoverned |
| --- | --- | --- |
| Active files | 2 | 242 |
| Expired candidates | 0 | 240 |
| What the next agent sees | the real code | the real code + 240 byproducts |

Every governed byproduct stays recoverable: rolling back the first loop's
draft restores it byte-for-byte in under a hundred milliseconds. The
structural result does not depend on the machine: the ungoverned workspace
grows linearly while the governed one stays flat.

The same audit produces a **workspace health score** from 0 to 100, combining
auditability, governance, rot burden and recycle readiness -- one number per
repo, suitable for a CI gate or a badge.

## Two new words, honestly

We propose two open vocabulary terms: **Metabolic Debt**, the accumulating
drag that unmanaged byproducts impose on every future loop; and **Workspace
Rot**, its failure mode. The opposite of rot is not emptiness; it is
rightness -- the right files, at the right time, with a verifiable history.

An honest disclaimer: the metaphor is not ours. "Information metabolism"
dates to the 1960s, and metabolic engineering is an established discipline in
biology. We claim the framing, not the words. The reference implementation is
[workspace-metabolism](https://github.com/metabolism-tools/workspace-metabolism),
MIT-licensed, zero-dependency, available on
[PyPI](https://pypi.org/project/workspace-metabolism/).

## The invitation

Agent loops are now factories. Factories have waste systems; ours do not yet.
If your agent workspaces rot faster than your code grows, that is not a
cleaning problem -- it is a missing layer of the stack.

Run `pip install workspace-metabolism`, run `wm init`, and give your workspace
a metabolism. Then tell us what breaks.
