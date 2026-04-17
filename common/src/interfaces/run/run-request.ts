import type { RunConfig } from '../agent/run-config.ts'

export interface RunRequest {
  diff?: string
  repoPath?: string
  config?: RunConfig
  apiKey?: string
}
