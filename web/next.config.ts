import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  experimental: {
    serverComponentsExternalPackages: [
      '@nexarq/agent-runtime',
      '@langchain/core',
      '@langchain/langgraph',
      '@langchain/anthropic',
      '@langchain/openai',
      '@langchain/google-genai',
      '@langchain/ollama',
    ],
  },
  transpilePackages: ['@nexarq/common', '@nexarq/agent-runtime'],
}

export default nextConfig
