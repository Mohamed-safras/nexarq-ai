import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on DevOps, infrastructure, and CI/CD concerns in this diff.

Check for:
- Docker images using 'latest' tag instead of pinned versions
- Running containers as root without necessity
- Secrets or credentials hardcoded in Dockerfiles or CI configs
- Missing health checks in Docker Compose or Kubernetes manifests
- CI pipelines missing test or lint steps
- Overly broad IAM permissions or firewall rules
- Terraform/IaC resources with public access where private is appropriate
- Missing resource limits (CPU/memory) in container specs`

export const devopsAgent: AgentDefinition = {
  name: 'devops',
  displayName: 'DevOps',
  description: 'Docker, CI/CD, IaC security, and infrastructure configuration',
  severity: 'medium',
  tier: 2,
  selectionHints: {
    filePaths: ['dockerfile', '.github', '/ci/', '.tf', 'k8s', 'docker-compose', '.yml', '.yaml', 'jenkinsfile', 'circleci'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
