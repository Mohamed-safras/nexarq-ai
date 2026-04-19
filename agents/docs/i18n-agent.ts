import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on internationalisation (i18n) issues in this diff.

Check for:
- User-facing strings hardcoded in English instead of using translation keys
- Date, time, or number formatting not using locale-aware formatters
- String concatenation to build translated sentences (order differs by language)
- Pluralisation handled with simple if/else instead of i18n plural rules
- RTL (right-to-left) layout assumptions broken for Arabic/Hebrew
- Currency values formatted without locale-aware currency formatters`

export const i18nAgent: AgentDefinition = {
  name: 'i18n',
  displayName: 'Internationalisation',
  description: 'Hardcoded strings, locale-unaware formatters, and RTL issues',
  severity: 'low',
  tier: 2,
  selectionHints: {
    filePaths: ['i18n', 'locale', 'translation', '/lang/', 'locales/'],
    diffContent: ['t(\'', 't("', 'translate(', 'i18n.', 'intl.'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
