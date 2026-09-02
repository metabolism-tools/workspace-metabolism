# Roadmap

Status: proposal / active development. The paradigm is bigger than the tool;
this roadmap tracks both.

## Shipped (v0.1.x)

- Policy-driven lifecycle CLI: `audit`, `clean` (recyclable), `rollback`,
  `purge`, `verify`, `status`; G1-G4 grades; hash-chained journal; protected
  windows; scheduling templates; zero dependencies; CI on three OSes.
- Narrative: Agentic Metabolic Engineering as the L5 layer of the agentic
  stack, with a one-liner ("loops keep the agent running; metabolism keeps the
  workspace alive"), a three-act story, Metabolic Debt / Workspace Rot
  vocabulary, and a reproducible 30-loop proof benchmark.
- Launch: v0.1.2 on PyPI, GitHub release, discussion announcement, and
  paste-ready copy for X, Zhihu and Xiaohongshu.

## In v0.4.0 (shipped)

- `wm gate`: MCP governance proxy — wraps any MCP stdio server; every
  `tools/call` is checked against `ai_governance` before forwarding, denied
  calls never reach the target, all decisions land in the journal. Tool
  names map to actions via `tool_patterns`; calls with `"preview": true`
  satisfy `requires_preview`. Documented as governance/audit, not a sandbox.
- `decision_id` execution chain: `govern` returns a `decision_id`; `clean` /
  `rollback` / `slim` accept `--decision-id`, so the journal shows the full
  intent -> decision -> execution chain with policy hashes at every step.

## In v0.3.0 (shipped)

- `wm slim`: in-place SQLite trimming for policy-registered databases (strip
  heavy JSON keys from one blob column, keep the newest N reference values,
  VACUUM above a reclaim threshold; journaled, dry-run by default). The
  DB-internal analogue of `clean`.
- `ai_governance` policy section, `wm govern` CLI command and `wm_govern` MCP
  tool: fail-closed decisions for read/write/execute/delete/network actions,
  with preview and human-approval requirements recorded in the journal.

## In v0.3.1 (shipped)

- Three policy-matching fixes found by real usage (the case study's
  dogfooding round): generic entries no longer shadow specific entries
  (longest match wins), directory-form entries match databases inside them
  (file + parent-path dual-base suffix matching), and most-specific-entry
  resolution in `explain`/`clean` planning. Regression tests for the real
  deployment shape.

## In v0.4.0 (shipped)

- `wm govern` CLI command and `wm_govern` MCP tool: fail-closed decisions for
  read/write/execute/delete/network actions, with preview and
  human-approval requirements recorded in the journal
  (`ai_governance` policy section).

## In v0.2.x (previous sprints)

- `wm init`: scaffold a `metabolism.json` policy file, like `git init`.
- Auto-discovery of `metabolism.json` / `.wm.json` (no `--registry` needed).
- JSON Schema for the policy file, so editors and agents can validate it.
- `wm explain <path>`: the nutrition label for any path.
- `wm health`: a 0-100 workspace health score, plus a shields.io badge output.
- `wm mcp`: a zero-dependency MCP stdio server so agents can run
  micro-metabolism themselves (clean stays dry-run by default).
- `examples/micro_metabolism.py` and `examples/ci-audit.yml`: the
  end-of-loop ritual and the CI health gate.

## Next

- **Agent framework integrations**: ready-made session-end hooks for Claude
  Code and Codex; an MCP client guide; DeepSeek Harness via
  `@deepseek-ai/dsh-mcp-client` ([docs/dsh-integration.md](docs/dsh-integration.md)).
- **Self-evolution accountability (v0.4+ direction)**: the `decision_id`
  chain (shipped in v0.4.0) gives journal-backed attribution of model-made
  changes. Remaining steps: automatic `turn/end` auditing (native DSH
  plugin), workspace health score as a cross-session fitness signal, and
  gate enforcement inside agent frameworks (not just the stdio proxy).
  Not yet wired into any loop — see the DSH discussion thread for the open
  design question.
- **Benchmark v2**: multi-profile workspaces (agent-heavy repo, data-science
  workspace, web project), 100-loop runs, audit-time and context-size curves.
- **Health badge hosting**: a hosted endpoint so the badge updates
  automatically (the CI workflow already generates the JSON).
- **Policy schema v2**: `owner` / `intent` / `review_after` review workflow;
  policy diffs and approval history in the journal.
- **Adoptions**: a public list of teams using the paradigm, and a "weird
  directory" collection that hardens the tool.

## Long term

- Metabolism policy as a standard project artifact, as common as `.gitignore`.
- Workspace health score as a standard, comparable metric across repos.
- Micro-metabolism as a first-class step of agentic loops (plan -> execute ->
  observe -> digest -> plan).
