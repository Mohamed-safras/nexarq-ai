import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Focus ONLY on test coverage gaps in this diff.

Check for:
- New functions or methods added without corresponding test cases
- Changed logic paths not covered by existing tests
- Error and edge cases not tested (empty input, null, boundary values)
- New public API surface with no integration tests
- Tests that only test the happy path and ignore failure cases
- Test helpers or mocks that may hide real behavior
- Critical business logic lacking any unit test coverage`

export const testCoverageAgent: AgentDefinition = {
  name: 'test_coverage',
  displayName: 'Test Coverage',
  description: 'Missing test cases for new logic, edge cases, and error paths',
  severity: 'medium',
  tier: 2,
  needsTools: true,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
