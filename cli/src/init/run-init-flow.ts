import { runWelcomeScreen } from '../output/tui/welcome-tui.ts'
import { runInitWizard } from '../output/tui/init-tui.ts'
import { getThemeByVariant } from '../output/tui/theme.ts'
import { saveConfig } from '../config/config-loader.ts'
import { storeApiKey } from '../auth/keyring.ts'
import { installHook } from '../git/hook-installer.ts'
import { printError } from '../output/formatter.ts'

/**
 * Shared first-run setup flow used by both the default action (index.ts)
 * and the `nexarq init` command.
 *
 * Runs: welcome screen → theme picker → provider/key wizard → hook install.
 * Throws on cancellation; callers should catch and exit.
 */
export async function runInitFlow(): Promise<void> {
  const variant = await runWelcomeScreen()
  const theme   = getThemeByVariant(variant)
  const wizard  = await runInitWizard(theme)

  if (wizard.apiKey) {
    await storeApiKey(wizard.provider, wizard.apiKey)
  }

  await saveConfig({
    provider:     wizard.provider,
    cloudConsent: wizard.cloudConsent,
    theme:        variant,
  })

  if (wizard.installPostCommit) await installHook('post-commit')
  if (wizard.installPrePush)    await installHook('pre-push')
}

export async function safeRunInitFlow(): Promise<boolean> {
  try {
    await runInitFlow()
    return true
  } catch (err) {
    printError(err instanceof Error ? err.message : String(err))
    return false
  }
}
