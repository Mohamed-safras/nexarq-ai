import { Command } from 'commander'
import { saveConfig } from '../config/config-loader.ts'
import { installHook } from '../git/hook-installer.ts'
import { storeApiKey } from '../auth/keyring.ts'
import { runWelcomeScreen } from '../output/tui/welcome-tui.ts'
import { runInitWizard } from '../output/tui/init-tui.ts'
import { getThemeByVariant } from '../output/tui/theme.ts'
import { printError } from '../output/formatter.ts'

export function initCommand(): Command {
  return new Command('init')
    .description('Interactive setup wizard — theme picker + provider config')
    .action(async () => {
      try {
        // Step 0: welcome screen + theme picker
        const variant = await runWelcomeScreen()
        const theme = getThemeByVariant(variant)

        // Steps 1-5: provider, API key, hooks, consent
        const wizard = await runInitWizard(theme)

        // Persist everything
        if (wizard.apiKey) {
          await storeApiKey(wizard.provider, wizard.apiKey)
        }

        await saveConfig({
          provider: wizard.provider,
          cloudConsent: wizard.cloudConsent,
          theme: variant,
        })

        if (wizard.installPostCommit) {
          await installHook('post-commit')
        }

        if (wizard.installPrePush) {
          await installHook('pre-push')
        }
      } catch (initError) {
        printError(initError instanceof Error ? initError.message : String(initError))
        process.exit(1)
      }
    })
}
