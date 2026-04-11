export interface TokenUsage {
  promptTokens: number
  completionTokens: number
  totalTokens: number
  estimatedCostUsd?: number
}
