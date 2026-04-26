import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  serverExternalPackages: [
    '@nexarq/agent-runtime',
    '@langchain/core',
    '@langchain/langgraph',
    '@langchain/anthropic',
    '@langchain/openai',
    '@langchain/google-genai',
    '@langchain/ollama',
  ],
  transpilePackages: ['@nexarq/common'],
}

export default nextConfig
