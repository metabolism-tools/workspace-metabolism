import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// Only packaged instructions are read. Loading the plugin never maintains files.
const skill = JSON.parse(readFileSync(new URL('./skill.json', import.meta.url), 'utf8'));
const resourceBase = {
  kind: 'directory',
  path: fileURLToPath(new URL('./skills/metabolic-maintenance/', import.meta.url)),
};

export const name = 'metabolic-maintenance';
export const inject = ['skills'];

export function apply(ctx) {
  const definition = {
    ...skill,
    invocation: { modelInvocable: true, userInvocable: true },
    provider: 'metabolism-tools-maintenance',
    source: 'bundled',
    resourceBase,
  };
  ctx.skills.registerProvider(() => ({
    name: definition.provider,
    // DSH's documented BUNDLED_SKILL_RANK is 600. Project skills take precedence.
    list: async () => [{ ...definition, content: undefined, rank: 600, locator: skill.name }],
    get: async (candidate) => candidate.locator === skill.name ? definition : undefined,
  }));
}
