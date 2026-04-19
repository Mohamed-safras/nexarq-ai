import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on accessibility (a11y) issues in this diff.

Check for:
- Images missing alt text or using empty alt on meaningful images
- Interactive elements (buttons, links) missing accessible labels
- Form inputs missing associated labels or aria-label
- Color as the only means of conveying information
- Keyboard navigation broken (missing tabIndex, focus traps)
- ARIA roles or attributes used incorrectly
- Missing landmark elements (main, nav, header, footer)
- Insufficient color contrast (WCAG AA requires 4.5:1 for normal text)`

export const accessibilityAgent: AgentDefinition = {
  name: 'accessibility',
  displayName: 'Accessibility',
  description: 'WCAG 2.1 violations, missing ARIA labels, keyboard navigation issues',
  severity: 'medium',
  tier: 2,
  selectionHints: {
    changeTypes: ['docs', 'feature'],
    filePaths: ['.css', '.scss', '.html', '.jsx', '.tsx', '.vue', 'aria'],
    diffContent: ['<button', '<input', '<img', '<a href', 'onClick', 'role='],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
