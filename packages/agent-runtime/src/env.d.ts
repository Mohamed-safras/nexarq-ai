// Ambient shims for Bun globals — replaced by @types/bun after `bun install`.

declare const process: {
  env: Record<string, string | undefined>
  cwd(): string
  exit(code?: number): never
  argv: string[]
}

declare function fetch(
  input: string | URL,
  init?: {
    method?: string
    headers?: Record<string, string>
    body?: string | null
  }
): Promise<{
  ok: boolean
  status: number
  json(): Promise<unknown>
  text(): Promise<string>
}>
