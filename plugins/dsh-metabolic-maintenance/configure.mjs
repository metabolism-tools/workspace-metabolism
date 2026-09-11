const args = process.argv.slice(2);
if (args.some(arg => arg !== '--with-wm') || args.length > 1) {
  console.error('Usage: node configure.mjs [--with-wm] > maintenance.patch.json');
  process.exit(1);
}
const entries = [{
  id: 'metabolic-maintenance',
  name: new URL('./index.js', import.meta.url).href,
}];
if (args.includes('--with-wm')) {
  entries.push({
    id: 'workspace-metabolism', name: '@deepseek-ai/dsh-mcp-client',
    config: {serverName: 'wm', transport: 'stdio', command: 'wm', args: ['mcp'], cwd: process.cwd()},
  });
}
// JSON is accepted by DSH's YAML patch reader. Write only to stdout.
console.log(JSON.stringify([{insert: entries}], null, 2));
