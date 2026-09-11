# Metabolic Maintenance for DSH

A native Cordis skill-provider plugin for DeepSeek Harness. It teaches the agent to maintain a workflow according to error consequences, preserve consumer evidence, and verify downstream work after changes and recovery.

This plugin supplies instructions on demand. It registers no cleanup hooks, runs no background jobs, and grants no permissions. Use WM's existing MCP integration when executable maintenance tools are wanted.

## Which part should I use?

| Part | Responsibility | Use it when | What it cannot establish |
| --- | --- | --- | --- |
| Metabolic Maintenance skill | Guides the agent's maintenance judgment and evidence collection | An agent must decide whether maintenance is needed and how to verify its result | Enforced permissions, model obedience, or business correctness |
| WM CLI / MCP tools | Audit, policy-based previews, reversible cleanup, integrity checks, and rollback | You need executable file-lifecycle operations | Whether a downstream research report, build, or other business result is correct |
| Your downstream consumer and acceptance check | Runs the affected workflow and checks its actual output | You need to accept maintenance or confirm recovery | Authorization for unrelated changes |

Use WM alone when an existing script already defines the maintenance and acceptance procedure. Use the skill alone with other adequate tools when the agent needs maintenance guidance. Combine them when the agent needs both guidance and WM operations. The skill is an advisory layer; it is not a decision authority or an enforcement boundary.

## The four rules in practice

| Rule | Meaning | Example |
| --- | --- | --- |
| Maintain for an actual reason | Identify a due policy, capacity limit, broken dependency, or explicit objective; otherwise take no action | A 30-day retention rule applies to an unused 45-day-old scratch report. A fresh report does not become a cleanup target merely because an agent is idle. |
| Match autonomy to error consequences | Assess affected scope, dependencies, isolation, and recovery. More serious consequences require stronger conditions before autonomous action, not just a lower confidence score | A regenerable cache can use bounded checks. Shared input evidence needs a known consumer, preserved provenance, and a tested recovery route. Unresolved high-impact choices go to the authorized human. |
| Preserve consumer evidence | Retain the information needed to reproduce and judge downstream results, not merely copies of the files being removed | Keep input identity, relevant policy/tool/consumer versions, acceptance criteria, actual output, and recovery material outside the cleanup target. |
| Verify downstream work after maintenance and recovery | Run the relevant consumer and compare its output with the agreed acceptance condition. Recheck after rollback | A report must still total 18 after cleanup. If cleanup breaks it, restoring files is only the first step: the report must produce 18 again. Missing verification leaves the outcome unresolved. |

Checks should be proportional. These rules do not require repeated approval for already authorized reversible work, or a research experiment for every cache cleanup.

## End-to-end example

[Run the isolated maintenance cycle](examples/README.md) or [view its recorded terminal output](examples/terminal-session.txt): assess a due scratch report, preview and execute WM cleanup, check a real file-reading consumer, and recover a deliberately broken fixture. It also demonstrates holding a cycle when its consumer is unknown. The example separates scripted execution from the DSH agent's proposed role; it is not evidence of autonomous model performance.

## Install from GitHub Release

Download the plugin `.tgz` from the [dsh-metabolic-maintenance-v0.1.2 release](https://github.com/metabolism-tools/workspace-metabolism/releases/tag/dsh-metabolic-maintenance-v0.1.2). Extract it into a directory you control; npm archives contain a `package/` directory. Keep that directory intact. No npm account, build step, or plugin dependency installation is required to load the extracted plugin. The optional runnable example separately requires Python and WM.

From the workspace you want to work on, generate a patch with the plugin's absolute location, then launch your existing DSH installation:

```sh
node /absolute/path/to/package/configure.mjs > maintenance.patch.json
npx @deepseek-ai/dsh web --patch ./maintenance.patch.json
```

Alternatively, add a plugin row to your existing DSH composition using the file URL of the extracted `index.js`:

```yaml
- insert:
    - id: metabolic-maintenance
      name: 'file:///absolute/path/to/package/index.js'
```

On Windows use a file URL, for example `file:///D:/tools/metabolic-maintenance/package/index.js`. The generator handles spaces and non-ASCII paths automatically. The standard DSH composition must provide its skills registry and skill tool. Remove the overlay/row to disable the plugin.

Ask the agent: **Use the metabolic-maintenance skill to assess this workspace's maintenance needs. Execute only authorized actions and verify the affected downstream results.**

The model can load it through `skill({name: "metabolic-maintenance"})`. The evaluation reference is available on demand; its contents are not added to every conversation step. Same-name project skills outrank this bundled provider, so check for a local override if the body differs.

## Pair with WM

Install `workspace-metabolism` into your chosen Python environment. Generate a combined patch from your target workspace:

```sh
node /absolute/path/to/package/configure.mjs --with-wm > maintenance.patch.json
```

This adds the same official MCP bridge used by the existing [WM integration](https://github.com/metabolism-tools/workspace-metabolism/blob/main/examples/dsh/wm.cordis.yml) and pins its working directory to where you generated the patch. WM's Python executable must be on the DSH process's PATH. If WM is already configured, use the skill-only patch to avoid duplicate plugin entries. Generated patches contain local paths; regenerate after moving directories and do not include them in public reports.

The skill can also use existing scripts. It does not require experimental `wm change` commands. WM integrity checks do not by themselves prove consumer correctness, and policy receipts do not authenticate human approval.

## Build and verify from source

From `plugins/dsh-metabolic-maintenance` in the WM repository:

```sh
npm ci --ignore-scripts
npm run build
npm test
npm pack
```

The canonical instructions live at `skills/metabolic-maintenance` in the repository root. Packaging generates an identical distributable copy; edit the canonical source, not generated assets.

Compatibility checks use the real Cordis `4.0.2` and DSH skill registry `0.0.1-rc.1`, covering discovery, loading, reference access, project override, and disposal. The provider follows the [official DSH skill API](https://github.com/deepseek-ai/deepseek-harness/blob/c291e7961a515f6d7af9304e7fd1d257929aef26/docs/subsystems/skills.md). These checks do not establish full DSH UI compatibility, model obedience, lower token costs, or production maintenance safety. DSH is evolving; keep the version boundary visible when diagnosing compatibility issues.
