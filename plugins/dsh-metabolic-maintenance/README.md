# Metabolic Maintenance for DSH

A native Cordis skill-provider plugin for DeepSeek Harness. It teaches the agent to maintain a workflow according to error consequences, preserve consumer evidence, and verify downstream work after changes and recovery.

This plugin supplies instructions on demand. It registers no cleanup hooks, runs no background jobs, and grants no permissions. Use WM's existing MCP integration when executable maintenance tools are wanted.

## Install from GitHub Release

Download the plugin `.tgz` from the [dsh-metabolic-maintenance-v0.1.0 release](https://github.com/metabolism-tools/workspace-metabolism/releases/tag/dsh-metabolic-maintenance-v0.1.0). Extract it into a directory you control; npm archives contain a `package/` directory. Keep that directory intact. No npm account, build step, or plugin dependency installation is required to load the extracted plugin.

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
