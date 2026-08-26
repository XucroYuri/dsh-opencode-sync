// Native DSH Cordis plugin for OpenCode -> DSH provider sync.
// Uses ctx.settings and ctx.credentials instead of shelling out to Python.
import { readFileSync, existsSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { spawnSync } from 'node:child_process'

export const name = 'dsh-opencode-sync'
export const description = 'Sync OpenCode provider config into DeepSeek Harness'
export const inject = ['settings', 'credentials']

function envName(provider) {
  return provider.replace(/[^A-Za-z0-9]+/g, '_').replace(/^_+|_+$/g, '').toUpperCase() + '_API_KEY'
}

function loadJson(path) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'))
  } catch {
    return {}
  }
}

import { readdirSync } from 'node:fs'

function findWindowsOpencodeReal() {
  const root = '/mnt/c/Users'
  if (!existsSync(root)) throw new Error('No /mnt/c/Users found; are you inside WSL?')
  for (const name of readdirSync(root)) {
    const base = join(root, name)
    const cfg = join(base, '.config/opencode/opencode.json')
    const auth = join(base, '.local/share/opencode/auth.json')
    if (existsSync(cfg) || existsSync(auth)) {
      return { user: base, config: cfg, auth }
    }
  }
  throw new Error('No OpenCode Windows config found under /mnt/c/Users')
}

function findWslOpencode() {
  const home = homedir()
  const cfg = join(home, '.config/opencode/opencode.json')
  const auth = join(home, '.local/share/opencode/auth.json')
  if (!existsSync(cfg) && !existsSync(auth)) throw new Error('No OpenCode WSL config found')
  return { user: home, config: cfg, auth }
}

function parseOpencodeModels(output) {
  const lines = output.split('\n')
  const entries = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i].trim()
    if (line && line.includes('/') && !line.startsWith('{') && !line.startsWith('}')) {
      let j = i + 1
      while (j < lines.length && lines[j].trim() === '') j++
      if (j < lines.length && lines[j].trim() === '{') {
        const text = lines.slice(j).join('\n')
        // Use a simple brace counter because JSON.parse needs full string.
        let depth = 0
        let end = -1
        for (let k = 0; k < text.length; k++) {
          if (text[k] === '{') depth++
          else if (text[k] === '}') {
            depth--
            if (depth === 0) { end = k + 1; break }
          }
        }
        if (end > 0) {
          try {
            const obj = JSON.parse(text.slice(0, end))
            entries.push([line, obj])
            const consumed = text.slice(0, end).split('\n').length
            i = j + consumed
            continue
          } catch {}
        }
      }
    }
    i++
  }
  return entries
}

function collectSecrets(opencodeCfg, auth) {
  const refs = {}
  const providerRef = {}
  const add = (provider, key) => {
    const ref = envName(provider)
    refs[ref] = key
    providerRef[provider] = ref
  }
  for (const [pid, pconf] of Object.entries(opencodeCfg.provider ?? {})) {
    if (!pconf || typeof pconf !== 'object') continue
    const opts = pconf.options && typeof pconf.options === 'object' ? pconf.options : {}
    const key = opts.apiKey || pconf.apiKey
    if (typeof key === 'string' && key) add(pid, key)
  }
  for (const [pid, aconf] of Object.entries(auth)) {
    if (!aconf || typeof aconf !== 'object') continue
    if (aconf.type === 'api' && typeof aconf.key === 'string' && aconf.key) add(pid, aconf.key)
  }
  return { refs, providerRef }
}

function buildProfiles(models, providerRef, existingProviders, preferredModels, includeAll) {
  const byProvider = {}
  for (const [full, meta] of models) {
    const idx = full.indexOf('/')
    const provider = full.slice(0, idx)
    const modelId = full.slice(idx + 1)
    ;(byProvider[provider] ??= []).push([modelId, meta])
  }
  const knownCatalog = new Set(['openai','deepseek','anthropic','google','xai','zai','opencode','github-copilot'])
  const providers = {}
  for (const [provider, modelList] of Object.entries(byProvider)) {
    if (!providerRef[provider]) continue
    const profile = { apiKeyEnv: providerRef[provider] }
    const first = modelList[0]?.[1] ?? {}
    const url = first.api?.url
    if (url) profile.baseURL = url
    const isKnown = knownCatalog.has(provider)
    if (!isKnown) profile.api = 'openai-completions'

    const existingProvider = existingProviders[provider]
    let existingModels = null
    if (existingProvider && Array.isArray(existingProvider.models)) existingModels = existingProvider.models

    let dshModels = []
    if (existingModels) {
      dshModels = existingModels
    } else if (isKnown && !includeAll) {
      dshModels = []
    } else {
      const pref = preferredModels[provider]
      for (const [modelId, meta] of modelList) {
        if (pref && !pref.has(modelId)) continue
        const entry = { id: modelId }
        if (meta.name && meta.name !== modelId) entry.name = meta.name
        if (meta.limit?.context) entry.contextWindow = meta.limit.context
        if (meta.limit?.output) entry.maxTokens = meta.limit.output
        const efforts = {}
        for (const [level, variant] of Object.entries(meta.variants ?? {})) {
          if (variant && typeof variant === 'object' && variant.effort) efforts[level] = variant.effort
        }
        if (Object.keys(efforts).length) entry.reasoningEfforts = efforts
        dshModels.push(entry)
      }
    }
    if (dshModels.length) profile.models = dshModels
    providers[provider] = profile
  }
  return providers
}

export async function apply(ctx) {
  const args = ctx.get('cmdlineArgs')?.get() ?? []
  if (args[0] !== 'opencode-sync') return

  const exit = ctx.get('appExit')
  const finish = (code) => { if (exit) exit(code) }

  try {
    const sourceArg = args.find((a, i) => a === '--source' && args[i+1]) ? args[args.indexOf('--source')+1] : 'auto'
    let src
    if (sourceArg === 'windows') src = findWindowsOpencodeReal()
    else if (sourceArg === 'wsl') src = findWslOpencode()
    else {
      try { src = findWindowsOpencodeReal() } catch { src = findWslOpencode() }
    }

    const opencodeCfg = loadJson(src.config)
    const auth = loadJson(src.auth)
    const { refs, providerRef } = collectSecrets(opencodeCfg, auth)
    if (Object.keys(providerRef).length === 0) {
      console.error('No API-key providers found in OpenCode config/auth.')
      finish(1); return
    }

    const proc = spawnSync('opencode', ['models', '--verbose'], { encoding: 'utf8', timeout: 60000 })
    if (proc.status !== 0) {
      console.error('Failed to run `opencode models --verbose`', proc.stderr || '')
      finish(1); return
    }
    const models = parseOpencodeModels(proc.stdout)

    const settings = ctx.get('settings')
    const credentials = ctx.get('credentials')
    if (!settings || !credentials) {
      console.error('dsh-opencode-sync requires settings and credentials services.')
      finish(1); return
    }

    const current = settings.get('llm-pi-ai') ?? {}
    const existingProviders = (current.providers && typeof current.providers === 'object') ? current.providers : {}

    const preferredModels = {}
    for (const key of ['model', 'small_model']) {
      const val = opencodeCfg[key]
      if (typeof val === 'string' && val.includes('/')) {
        const idx = val.indexOf('/')
        const provider = val.slice(0, idx)
        const modelId = val.slice(idx + 1)
        ;(preferredModels[provider] ??= new Set()).add(modelId)
      }
    }

    const dryRun = args.includes('--dry-run')
    const includeAll = args.includes('--include-all-models')
    const providers = buildProfiles(models, providerRef, existingProviders, preferredModels, includeAll)

    if (dryRun) {
      console.log('# Would write credentials refs:')
      console.log(JSON.stringify(refs, null, 2))
      console.log('# Would write llm-pi-ai providers:')
      console.log(JSON.stringify(providers, null, 2))
      finish(0); return
    }

    for (const [ref, key] of Object.entries(refs)) {
      await credentials.set(ref, key)
    }
    await settings.update('llm-pi-ai', { providers })
    console.log('Updated credentials and settings.')
    console.log('Providers:', Object.keys(providers).join(', '))
    finish(0)
  } catch (error) {
    console.error('dsh-opencode-sync failed:', error)
    finish(1)
  }
}
