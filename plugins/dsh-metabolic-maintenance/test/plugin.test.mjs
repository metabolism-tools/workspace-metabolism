import assert from 'node:assert/strict';
import { readFile, mkdtemp, rm, realpath } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { test } from 'node:test';
import { Context } from '@deepseek-ai/cordis';
import SkillService, { renderSkillContent } from '@deepseek-ai/dsh-skill';
import Loader from '@deepseek-ai/cordis-plugin-loader';
import { applyEntryPatches } from '@deepseek-ai/cordis-plugin-include';
import * as plugin from '../index.js';

test('real DSH registry discovers, loads and removes the packaged skill', async () => {
  const ctx = new Context();
  await ctx.plugin(SkillService).await();
  const fork = ctx.plugin(plugin);
  await fork.await();
  try {
    const catalog = await ctx.skills.list();
    assert.equal(catalog.length, 1);
    assert.equal(catalog[0].name, 'metabolic-maintenance');
    assert.equal(catalog[0].content, undefined);
    assert.deepEqual(catalog[0].invocation, {modelInvocable: true, userInvocable: true});
    const loaded = await ctx.skills.get('metabolic-maintenance');
    const canonical = await readFile(new URL('../../../skills/metabolic-maintenance/SKILL.md', import.meta.url), 'utf8');
    assert.equal(loaded.content, canonical.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '').trim());
    const reference = await readFile(join(loaded.resourceBase.path, 'references/evaluation.md'), 'utf8');
    assert.match(reference, /Missing acceptance is unknown/);
    assert.match(await readFile(join(loaded.resourceBase.path, 'references/maintenance-observation.md'), 'utf8'), /missing completion evidence/);
    assert.match(await readFile(join(loaded.resourceBase.path, 'references/observation-record.md'), 'utf8'), /Discovery delay/);
    assert.match(renderSkillContent(loaded), /<skill_content name="metabolic-maintenance">/);
    assert.equal(await ctx.skills.get('unknown-skill'), undefined);
    await fork.dispose();
    assert.deepEqual(await ctx.skills.list(), []);
  } finally {
    await ctx.fiber.dispose();
  }
});

test('generated patch loads the packed plugin from another directory through Cordis', async () => {
  const packageRoot = fileURLToPath(new URL('../', import.meta.url));
  const packed = JSON.parse(execFileSync(process.execPath, [process.env.npm_execpath, 'pack', '--json'], {
    cwd: packageRoot, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
  }))[0];
  assert.equal(packed.entryCount, 15);
  assert.ok(packed.files.some(file => file.path === 'examples/maintenance_cycle.py'));
  assert.ok(packed.files.some(file => file.path === 'examples/maintenance_observation.py'));
  assert.ok(packed.files.some(file => file.path === 'examples/observation-session.json'));
  assert.ok(!packed.files.some(file => /node_modules|test\/|agents\/|build\.mjs|__pycache__|\.pyc$/.test(file.path)));
  const temporary = await mkdtemp(join(tmpdir(), 'wm-dsh-plugin-'));
  const ctx = new Context();
  try {
    execFileSync('tar', ['-xzf', join(packageRoot, packed.filename), '-C', temporary]);
    const observed = JSON.parse(execFileSync(process.env.PYTHON || 'python',
      ['-I', join(temporary, 'package', 'examples', 'maintenance_observation.py')],
      {cwd: tmpdir(), encoding: 'utf8', timeout: 30000}));
    const recorded = JSON.parse(await readFile(join(temporary, 'package', 'examples', 'observation-session.json'), 'utf8'));
    assert.deepEqual(observed, recorded);
    const configure = join(temporary, 'package', 'configure.mjs');
    const patch = JSON.parse(execFileSync(process.execPath, [configure], {cwd: tmpdir(), encoding: 'utf8'}));
    assert.equal(patch[0].insert.length, 1);
    const entries = applyEntryPatches([], patch, (message) => {throw new Error(message);});
    await ctx.plugin(SkillService).await();
    await ctx.plugin(Loader, {baseUrl: pathToFileURL(tmpdir() + '/').href}).await();
    await ctx.loader.root.update(entries);
    await ctx.loader.await();
    const loaded = await ctx.skills.get('metabolic-maintenance');
    assert.equal(loaded.provider, 'metabolism-tools-maintenance');
    assert.match(await readFile(join(loaded.resourceBase.path, 'references/evaluation.md'), 'utf8'), /Research question/);
    assert.match(await readFile(join(loaded.resourceBase.path, 'references/maintenance-observation.md'), 'utf8'), /missing completion evidence/);
    assert.match(await readFile(join(loaded.resourceBase.path, 'references/observation-record.md'), 'utf8'), /Discovery delay/);
    const combined = JSON.parse(execFileSync(process.execPath, [configure, '--with-wm'], {cwd: temporary, encoding: 'utf8'}));
    assert.equal(combined[0].insert.length, 2);
    assert.equal(await realpath(combined[0].insert[1].config.cwd), await realpath(temporary));
    assert.deepEqual(combined[0].insert[1].config.args, ['mcp']);
    assert.throws(() => execFileSync(process.execPath, [configure, '--execute'], {stdio: 'pipe'}));
  } finally {
    await ctx.fiber.dispose();
    // mkdtemp created this exact directory; no user-supplied deletion target.
    assert.ok(temporary.startsWith(join(tmpdir(), 'wm-dsh-plugin-')));
    await rm(temporary, {recursive: true, force: true});
  }
});

test('project provider overrides bundled rules and disposal restores the bundle', async () => {
  const ctx = new Context();
  await ctx.plugin(SkillService).await();
  await ctx.plugin(plugin).await();
  const project = ctx.plugin({inject: ['skills'], apply(child) {
    const value = {
      name: 'metabolic-maintenance', description: 'Project-specific maintenance rules',
      source: 'project-dsh', provider: 'test-project',
      invocation: {modelInvocable: true, userInvocable: true},
    };
    child.skills.registerProvider(() => ({
      name: value.provider,
      list: async () => [{...value, rank: 100, locator: 'project'}],
      get: async () => ({...value, content: 'Use the project retention policy.'}),
    }));
  }});
  await project.await();
  try {
    assert.equal((await ctx.skills.get('metabolic-maintenance')).provider, 'test-project');
    await project.dispose();
    assert.equal((await ctx.skills.get('metabolic-maintenance')).provider, 'metabolism-tools-maintenance');
  } finally {
    await ctx.fiber.dispose();
  }
});
