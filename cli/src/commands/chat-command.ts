import { Command } from 'commander'
import { Input, Text } from '@opentui/core'
import { THEME } from '../output/tui/theme.ts'
import { loadConfig } from '../config/config-loader.ts'
import { createPageTUI } from '../lib/tui-page.ts'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/**
 * nexarq chat
 *
 * Persistent conversation about your codebase.
 * Each turn runs the explain agent with full chat history injected.
 * History is kept in-memory only — session ends on exit.
 *
 * Token cost: scales with conversation length.
 * Mitigation: history is summarised after 20 turns to keep context bounded.
 */
export function chatCommand(): Command {
  return new Command('chat')
    .description('Chat with Nexarq about your codebase')
    .option('-d, --dir <path>', 'Project root directory')
    .action(async (options: { dir?: string }) => {
      const config = await loadConfig()
      const workingDirectory = options.dir ?? process.cwd()

      const tui = await createPageTUI('CHAT  ·  Ctrl+C to exit', 'CONVERSATION', { exitOnCtrlC: false })
      const history: ChatMessage[] = []

      // Add input row between body panel and status footer
      const inputBox = Input({
        placeholder: 'Ask about your code...',
        width: '100%',
        textColor: THEME.fg,
        backgroundColor: THEME.bgAlt,
      })
      // Insert input above the status line (before the last child / footer)
      const rootNode = tui.renderer.root as unknown as {
        getChildren(): unknown[]
        add(child: unknown, index?: number): void
      }
      rootNode.add(inputBox, rootNode.getChildren().length - 1)

      tui.status.content = '  Ready'
      inputBox.focus()

      function appendMessage(role: 'user' | 'assistant', content: string): void {
        const color = role === 'user' ? THEME.cyan : THEME.fg
        const prefix = role === 'user' ? '  You: ' : '  Nexarq: '
        content.split('\n').forEach((line, index) => {
          tui.body.add(Text({
            content: index === 0 ? `${prefix}${line}` : `         ${line}`,
            fg: color,
          }))
        })
        tui.body.add(Text({ content: '', fg: THEME.fg }))
      }

      async function handleSubmit(userMessage: string): Promise<void> {
        if (!userMessage.trim()) return

        history.push({ role: 'user', content: userMessage })
        appendMessage('user', userMessage)
        tui.status.content = '  Thinking...'

        // Summarise history if it grows beyond 20 turns (token safety)
        const historyContext = history.length > 20
          ? `[Earlier conversation summarised]\n${history.slice(-6).map((msg) => `${msg.role}: ${msg.content}`).join('\n')}`
          : history.slice(-10).map((msg) => `${msg.role}: ${msg.content}`).join('\n')

        let reply = ''
        try {
          const { runOrchestrator } = await import('@nexarq/agent-runtime')
          const result = await runOrchestrator({
            task: `You are a helpful code review assistant. Answer concisely.

Chat history:
${historyContext}

User: ${userMessage}`,
            triggerSource: 'on-demand',
            workingDirectory,
            runConfig: {
              provider: config.provider,
              ...(config.model ? { model: config.model } : {}),
              mode: 'smart',
              agents: ['explain'],
            },
            onEvent: (event) => {
              if (event.type === 'agent:chunk') {
                reply += event.text
              }
            },
          })

          reply = result.finalOutput.trim() || reply.trim() || 'No response generated.'
        } catch (error) {
          reply = `Error: ${error instanceof Error ? error.message : String(error)}`
        }

        history.push({ role: 'assistant', content: reply })
        appendMessage('assistant', reply)
        tui.status.content = '  Ready'
      }

      inputBox.on('enter', (value: string) => {
        void handleSubmit(value)
      })

      tui.renderer.keyInput.on('keypress', (event) => {
        if (event.ctrl && event.name === 'c') {
          tui.renderer.destroy()
          process.exit(0)
        }
      })

      appendMessage('assistant', 'Hi! Ask me anything about your codebase. I can review diffs, explain code, or discuss findings.')
    })
}
