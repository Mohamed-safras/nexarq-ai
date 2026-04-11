import type { RunConfig } from '../agent/run-config.js'

export interface RunRequest {
  diff?: string
  repoPath?: string
  config?: RunConfig
  apiKey?: string
}
