import { writeFileSync, readFileSync, existsSync, mkdirSync, chmodSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'

const TOKEN_PATH = join(homedir(), '.nexarq', '.token')
const GITHUB_CLIENT_ID = process.env['NEXARQ_GITHUB_CLIENT_ID'] ?? ''

export interface LoginResult {
  token: string
  username: string
  name: string
}

export async function startGitHubDeviceFlow(): Promise<LoginResult> {
  if (!GITHUB_CLIENT_ID) {
    throw new Error('NEXARQ_GITHUB_CLIENT_ID not configured')
  }

  // Step 1: Request device code
  const deviceResponse = await fetch('https://github.com/login/device/code', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: GITHUB_CLIENT_ID, scope: 'read:user' }),
  })
  const deviceData = await deviceResponse.json() as {
    device_code: string
    user_code: string
    verification_uri: string
    interval: number
    expires_in: number
  }

  console.log(`\n  Go to: ${deviceData.verification_uri}`)
  console.log(`  Enter code: ${deviceData.user_code}\n`)

  // Open browser
  try {
    const open = await import('open')
    await open.default(deviceData.verification_uri)
  } catch {
    // Browser open failed — user copies manually
  }

  // Step 2: Poll for token
  const token = await pollForToken(deviceData.device_code, deviceData.interval)

  // Step 3: Fetch user info
  const userResponse = await fetch('https://api.github.com/user', {
    headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json' },
  })
  const userData = await userResponse.json() as { login: string; name: string }

  // Save token
  mkdirSync(join(homedir(), '.nexarq'), { recursive: true })
  writeFileSync(TOKEN_PATH, JSON.stringify({ token, username: userData.login }), 'utf-8')
  chmodSync(TOKEN_PATH, 0o600)

  return { token, username: userData.login, name: userData.name ?? userData.login }
}

async function pollForToken(deviceCode: string, intervalSeconds: number): Promise<string> {
  const maxAttempts = 30
  let attempts = 0

  while (attempts < maxAttempts) {
    await sleep(intervalSeconds * 1_000)
    attempts++

    const tokenResponse = await fetch('https://github.com/login/oauth/access_token', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: GITHUB_CLIENT_ID,
        device_code: deviceCode,
        grant_type: 'urn:ietf:params:oauth:grant-type:device_code',
      }),
    })
    const tokenData = await tokenResponse.json() as {
      access_token?: string
      error?: string
    }

    if (tokenData.access_token) return tokenData.access_token
    if (tokenData.error === 'access_denied') throw new Error('Login cancelled')
    if (tokenData.error === 'expired_token') throw new Error('Device code expired — try again')
  }

  throw new Error('Login timed out')
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

export function getSavedToken(): { token: string; username: string } | null {
  if (!existsSync(TOKEN_PATH)) return null
  const rawData = readFileSync(TOKEN_PATH, 'utf-8')
  return JSON.parse(rawData) as { token: string; username: string }
}
