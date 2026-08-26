#!/usr/bin/env node
// Standalone CLI wrapper for dsh-opencode-sync.
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

if (process.argv[2] === '--version' || process.argv[2] === '-v') {
  const { readFileSync } = await import('node:fs')
  const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))
  console.log(pkg.version)
  process.exit(0)
}

const script = fileURLToPath(new URL('../src/dsh_opencode_sync.py', import.meta.url))
const result = spawnSync('python3', [script, ...process.argv.slice(2)], { stdio: 'inherit' })
process.exit(result.status ?? 1)
