import { confirm, input, select } from '@inquirer/prompts'
import { execSync } from 'child_process'
import type { ProviderName } from '@nexarq/common/types'
import { PROVIDER_MODELS, PROVIDER_DEFAULT_MODELS } from '@nexarq/common/constants'
import type { NexarqTheme } from './theme.ts'
import { HEADER_LINE_COUNT, printHeader } from './welcome-tui.ts'

export interface InitWizardResult {
  provider: ProviderName
  model: string
  apiKey?: string
  installPostCommit: boolean
  installPrePush: boolean
  cloudConsent: boolean
}

function isGitRepo(): boolean {
  try {
    execSync('git rev-parse --git-dir', { stdio: 'pipe' })
    return true
  } catch {
    return false
  }
}

// Erase `n` lines above the cursor and reposition there, ready to print fresh content.
function eraseStepArea(n: number): void {
  if (n <= 0) return
  process.stdout.write(`\x1b[${n}A\x1b[J`)
}

/**
 * runInitWizard
 *
 * Setup wizard: provider → API key → hooks → consent.
 * Step descriptions live inside each inquirer `message` so they can never be
 * erased by inquirer's own rendering. The shared header is reprinted per step.
 */
export async function runInitWizard(theme: NexarqTheme): Promise<InitWizardResult> {
  // linesAbove = lines currently on screen (header + previous step's 1 answer line).
  // welcome-tui leaves HEADER_LINE_COUNT lines on screen before handing off here.
  let linesAbove = HEADER_LINE_COUNT

  // ── Choose provider ───────────────────────────────────────────────────────
  eraseStepArea(linesAbove)
  printHeader(theme)

  const provider = await select<ProviderName>({
    message: 'Step 2 · Choose your LLM provider\n',
    choices: [
      { name: 'Ollama    (local, private, no API key needed)', value: 'ollama' },
      { name: 'OpenAI    (GPT-4o, requires API key)', value: 'openai' },
      { name: 'Anthropic (Claude, requires API key)', value: 'anthropic' },
      { name: 'Google    (Gemini, requires API key)', value: 'google' },
      { name: 'MiniMax   (~$0.10/1M tokens, ultra-cheap)', value: 'minimax' },
    ],
  })
  linesAbove = HEADER_LINE_COUNT + 1

  // ── Choose model ──────────────────────────────────────────────────────────
  eraseStepArea(linesAbove)
  printHeader(theme)

  const model = await select<string>({
    message: 'Step 3 · Choose your model\n',
    choices: PROVIDER_MODELS[provider].map((m) => ({ name: m, value: m })),
    default: PROVIDER_DEFAULT_MODELS[provider],
  })
  linesAbove = HEADER_LINE_COUNT + 1

  // Determine whether we're inside a git repo — skip hook prompts if not
  const hasGit = isGitRepo()

  // Total steps: base 3 (theme + provider + model) + optional API key + git hooks + consent
  const TOTAL = 3 + (provider !== 'ollama' ? 1 : 0) + (hasGit ? 2 : 0) + (provider !== 'ollama' ? 1 : 0)

  // ── API key (non-ollama only) ─────────────────────────────────────────────
  let apiKey: string | undefined

  if (provider !== 'ollama') {
    const providerLabel = provider.charAt(0).toUpperCase() + provider.slice(1)

    eraseStepArea(linesAbove)
    printHeader(theme)

    apiKey = await input({
      message: `Step 4 / ${TOTAL} · Enter your ${providerLabel} API key`,
      transformer: (value) => {
        if (value.length > 8) return value.slice(0, 4) + '...' + value.slice(-4)
        return value
      },
    })

    process.stdout.write('\x1b[2K  (stored securely in system keyring, never logged)\n')
    linesAbove = HEADER_LINE_COUNT + 1 + 1
  }

  // ── Git hooks (only shown when inside a git repo) ─────────────────────────
  let installPostCommit = false
  let installPrePush = false

  if (hasGit) {
    const postStep = provider === 'ollama' ? 4 : 5

    eraseStepArea(linesAbove)
    printHeader(theme)

    installPostCommit = await confirm({
      message: `Step ${postStep} / ${TOTAL} · Install post-commit hook?  (auto-reviews every git commit)`,
      default: false,
    })
    linesAbove = HEADER_LINE_COUNT + 1

    eraseStepArea(linesAbove)
    printHeader(theme)

    installPrePush = await confirm({
      message: `Step ${postStep + 1} / ${TOTAL} · Install pre-push hook?  (blocks push on CRITICAL or HIGH findings)`,
      default: false,
    })
    linesAbove = HEADER_LINE_COUNT + 1
  }

  // ── Cloud consent (non-ollama only) ───────────────────────────────────────
  let cloudConsent = false

  if (provider !== 'ollama') {
    eraseStepArea(linesAbove)
    printHeader(theme)

    cloudConsent = await confirm({
      message: `Step ${TOTAL} / ${TOTAL} · Send diffs to ${provider}?  (only diffs, never your full codebase)`,
      default: true,
    })
    linesAbove = HEADER_LINE_COUNT + 1
  }

  // ── Done ──────────────────────────────────────────────────────────────────
  eraseStepArea(linesAbove)
  printHeader(theme)
  process.stdout.write('\x1b[2K  Setup complete\n')
  process.stdout.write('\x1b[2K\n')
  process.stdout.write('\x1b[2K  Run nexarq run to test your first review.\n')
  process.stdout.write('\x1b[2K  Run nexarq doctor to verify your setup.\n')
  process.stdout.write('\x1b[2K\n')

  return {
    provider,
    model,
    ...(apiKey?.trim() ? { apiKey: apiKey.trim() } : {}),
    installPostCommit,
    installPrePush,
    cloudConsent,
  }
}
