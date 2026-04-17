import { join } from 'path'
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs'
import { homedir } from 'os'
import type { ProviderName } from '@nexarq/common/types'
import type { ThemeVariant } from '../output/tui/theme.ts'
import chalk from 'chalk'

const CONFIG_DIR = join(homedir(), '.nexarq')
const CONFIG_PATH = join(CONFIG_DIR, 'config.json')

export interface NexarqConfig {
  provider: ProviderName
  model?: string
  defaultAgents?: string[]
  cloudConsent: boolean
  webApiUrl?: string
  apiKey?: string
  theme?: ThemeVariant
  /** Whether nexarq auto-runs after every commit/push. Default true. */
  autoRun?: boolean
}

const DEFAULT_CONFIG: NexarqConfig = {
  provider: 'ollama',
  cloudConsent: false,
  theme: 'dark',
}

/** True if no global config file exists — i.e. first install. */
export function isFirstRun(): boolean {
  return !existsSync(CONFIG_PATH)
}

export async function loadConfig(): Promise<NexarqConfig> {
  // Project-local config takes priority
  const localConfigPath = join(process.cwd(), '.nexarq', 'config.json')
  if (existsSync(localConfigPath)) {
    const rawLocalConfig = readFileSync(localConfigPath, 'utf-8')
    return { ...DEFAULT_CONFIG, ...JSON.parse(rawLocalConfig) }
  }

  if (!existsSync(CONFIG_PATH)) return DEFAULT_CONFIG

  const rawConfig = readFileSync(CONFIG_PATH, 'utf-8')
  return { ...DEFAULT_CONFIG, ...JSON.parse(rawConfig) }
}

export async function saveConfig(config: Partial<NexarqConfig>): Promise<void> {
  mkdirSync(CONFIG_DIR, { recursive: true })
  const currentConfig = await loadConfig()
  const mergedConfig = { ...currentConfig, ...config }
  writeFileSync(CONFIG_PATH, JSON.stringify(mergedConfig, null, 2), 'utf-8')
}

export function showConfig(config: NexarqConfig): void {
  console.log(chalk.cyan('\nNexarq Configuration\n'))
  const entries: Array<[string, string]> = [
    ['provider',      config.provider],
    ['model',         config.model ?? '(auto)'],
    ['cloudConsent',  String(config.cloudConsent)],
    ['defaultAgents', config.defaultAgents?.join(', ') ?? '(context-selected)'],
    ['config file',   CONFIG_PATH],
  ]
  for (const [key, value] of entries) {
    console.log(`  ${chalk.gray(key.padEnd(16))} ${value}`)
  }
  console.log()
}
