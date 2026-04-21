import { Command } from 'commander'
import { Input, Text } from '@opentui/core'
import { resolve, relative } from 'node:path'
import { loadConfig } from '../config/config-loader.ts'
import { createEditSession } from '../lib/edit-approval.ts'
import { streamingApproveEdit } from '../lib/streaming-preview.ts'
import { createPageTUI } from '../lib/tui-page.ts'

export function chatCommand(): Command {
  return new Command('chat')
    .description('Chat with Nexarq about your codebase')
    .option('-d, --dir <path>', 'Project root directory')
    .action(async (options: { dir?: string }) => {
      const config = await loadConfig()
      const workingDirectory = options.dir ?? process.cwd()

      const { runConversationTurn } = await import('@nexarq/agent-runtime')
      const runConfig = {
        provider: config.provider,
        ...(config.model ? { model: config.model } : {}),
        unsafeShell: config.unsafeShell ?? false,
      }

      const tui = await createPageTUI('CHAT  ·  Ctrl+C to exit', 'CONVERSATION', { exitOnCtrlC: false })
      const { theme } = tui
      const editSession = createEditSession()
      const onBeforeWrite = async (filePath: string, oldContent: string | null, newContent: string, line?: number): Promise<boolean> => {
        tui.renderer.destroy()
        const fullPath    = resolve(workingDirectory, filePath)
        const displayPath = relative(workingDirectory, fullPath).replace(/\\/g, '/')
        process.stdout.write('\n')
        const decision = await streamingApproveEdit({ displayPath, fullPath, oldContent: oldContent ?? '', newContent, session: editSession, workingDirectory })
        return decision === 'yes'
      }

      const inputBox = Input({
        placeholder: 'Ask about your code...',
        width: '100%',
        textColor: theme.fg,
        backgroundColor: theme.bgAlt,
      })
      const rootNode = tui.renderer.root as unknown as {
        getChildren(): unknown[]
        add(child: unknown, index?: number): void
      }
      rootNode.add(inputBox, rootNode.getChildren().length - 1)

      tui.status.content = '  Ready'
      inputBox.focus()

      function appendMessage(role: 'user' | 'assistant', content: string): void {
        const color  = role === 'user' ? theme.cyan : theme.fg
        const prefix = role === 'user' ? '  You: ' : '  Nexarq: '
        content.split('\n').forEach((line, index) => {
          tui.body.add(Text({
            content: index === 0 ? `${prefix}${line}` : `         ${line}`,
            fg: color,
          }))
        })
        tui.body.add(Text({ content: '', fg: theme.fg }))
      }

      async function handleSubmit(userMessage: string): Promise<void> {
        if (!userMessage.trim()) return

        appendMessage('user', userMessage)
        tui.status.content = '  Thinking...'

        try {
          const result = await runConversationTurn({
            userMessage,
            workingDirectory,
            runConfig,
            onBeforeWrite,
          })

          appendMessage('assistant', result.response)

          if (result.suggestedFollowups.length > 0) {
            const hints = result.suggestedFollowups.slice(0, 3).map((s, i) => `${i + 1}. ${s}`).join('  ')
            tui.body.add(Text({ content: `  → ${hints}`, fg: theme.fgDim }))
            tui.body.add(Text({ content: '', fg: theme.fg }))
          }
        } catch (error) {
          appendMessage('assistant', `Error: ${error instanceof Error ? error.message : String(error)}`)
        }

        tui.status.content = '  Ready'
      }

      inputBox.on('enter', (value: string) => { void handleSubmit(value) })

      tui.renderer.keyInput.on('keypress', (event) => {
        if (event.ctrl && event.name === 'c') {
          tui.renderer.destroy()
          process.exit(0)
        }
      })

      appendMessage('assistant', 'Hi! Ask me anything about your codebase — I can review, implement, explain, search docs, or browse the web.')
    })
}
