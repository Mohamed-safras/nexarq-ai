export const BLOCKED_FILE_NAMES = new Set([
  '.env',
  '.env.local',
  '.env.production',
  '.env.staging',
  'credentials.json',
  'serviceaccount.json',
  'keystore.jks',
  '.netrc',
  '.npmrc',
  '.pypirc',
  'id_rsa',
  'id_ed25519',
])

export const ALLOWED_EXTENSIONS = new Set([
  '.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java',
  '.rb', '.php', '.swift', '.kt', '.scala', '.cs', '.cpp', '.c',
  '.h', '.sh', '.bash', '.yaml', '.yml', '.toml', '.json',
  '.env.example', '.sql', '.graphql', '.proto', '.md', '.txt',
  '.html', '.css', '.tf', '.hcl', '.dockerfile', '.xml',
  '.ini', '.cfg', '.lock',
])

export const REDACTION_PATTERNS = [
  /(?:api[_-]?key|apikey)\s*[:=]\s*['"]?[\w\-]{20,}['"]?/gi,
  /(?:password|passwd|secret|token)\s*[:=]\s*['"]?.{8,}['"]?/gi,
  /Bearer\s+[A-Za-z0-9\-._~+/]+=*/g,
  /AKIA[0-9A-Z]{16}/g,
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/g,
  /(?:postgres|mysql|mongodb|redis):\/\/[^:]+:[^@]+@/gi,
  /[A-Za-z0-9+/]{40,}={0,2}/g,
] as const

export const INJECTION_PATTERNS = [
  /ignore previous instructions/i,
  /you are now/i,
  /disregard your system prompt/i,
  /jailbreak/i,
  /DAN mode/i,
  /<\|system\|>/i,
] as const
