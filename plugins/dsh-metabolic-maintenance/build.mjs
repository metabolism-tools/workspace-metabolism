import { readFile, writeFile, mkdir, copyFile } from 'node:fs/promises';

const root = new URL('../../', import.meta.url);
const target = new URL('./', import.meta.url);
const relative = 'skills/metabolic-maintenance/';
const source = await readFile(new URL(relative + 'SKILL.md', root), 'utf8');
const match = source.match(/^---\r?\nname: ([a-z0-9-]+)\r?\ndescription: ("[^\r\n]*")\r?\n---\r?\n([\s\S]*)$/);
if (!match || match[1] !== 'metabolic-maintenance') {
  throw new Error('Canonical skill format changed; review the bundle metadata extraction.');
}
const skill = { name: match[1], description: JSON.parse(match[2]), content: match[3].trim() };
await mkdir(new URL(relative + 'references/', target), { recursive: true });
for (const file of ['SKILL.md', 'references/evaluation.md',
  'references/maintenance-observation.md', 'references/observation-record.md']) {
  await copyFile(new URL(relative + file, root), new URL(relative + file, target));
}
await copyFile(new URL('LICENSE', root), new URL('LICENSE', target));
await writeFile(new URL('skill.json', target), JSON.stringify(skill, null, 2) + '\n');
console.error('Built DSH plugin from canonical metabolic-maintenance skill.');
