// Minimal DSH Cordis command wrapper around the Python CLI.
// It avoids extra dependencies so it can be installed as a local file package.
import { spawnSync } from 'node:child_process'

export const name = 'dsh-opencode-sync'
export const description = 'Sync OpenCode provider config into DeepSeek Harness'

export function apply(ctx) {
  const args = ctx.get('cmdlineArgs')?.get() ?? []
  if (args[0] !== 'opencode-sync') return

  const result = spawnSync('dsh-opencode-sync', args.slice(1), {
    stdio: 'inherit',
    shell: false,
  })

  const exit = ctx.get('appExit')
  if (exit) exit(result.status ?? 1)
}
