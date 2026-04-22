import * as vscode from 'vscode'
import { reviewState } from './state'
import { ReviewPanel } from './panel'
import { GhostTextController, NexarqCodeActionProvider, InlineDiffController } from './providers'
import { runNexarqCli } from './runner'

export function activate(context: vscode.ExtensionContext): void {
  const ghostText = new GhostTextController()
  const inlineDiff = new InlineDiffController()

  context.subscriptions.push(ghostText, inlineDiff)

  // Propagate state changes to all providers
  const unsubscribe = reviewState.subscribe((run) => {
    if (run) {
      ghostText.applyRun(run)
      for (const editor of vscode.window.visibleTextEditors) {
        inlineDiff.applyToEditor(editor)
      }
    } else {
      ghostText.clear()
      inlineDiff.clear()
    }
  })
  context.subscriptions.push({ dispose: unsubscribe })

  // Re-apply decorations when a new editor becomes visible
  context.subscriptions.push(
    vscode.window.onDidChangeVisibleTextEditors((editors) => {
      const run = reviewState.get()
      if (!run) return
      ghostText.applyRun(run)
      for (const editor of editors) {
        inlineDiff.applyToEditor(editor)
      }
    })
  )

  // Code actions provider — all file types
  context.subscriptions.push(
    vscode.languages.registerCodeActionsProvider(
      { scheme: 'file' },
      new NexarqCodeActionProvider(),
      { providedCodeActionKinds: NexarqCodeActionProvider.providedCodeActionKinds }
    )
  )

  // Comment the newly inserted suggestion line using VS Code's own language rules
  context.subscriptions.push(
    vscode.commands.registerCommand(
      'nexarq.commentInsertedLine',
      async (uri: vscode.Uri, insertedLineIndex: number) => {
        const document = await vscode.workspace.openTextDocument(uri)
        const editor = await vscode.window.showTextDocument(document)
        const position = new vscode.Position(insertedLineIndex, 0)
        editor.selection = new vscode.Selection(position, position)
        await vscode.commands.executeCommand('editor.action.commentLine')
      }
    )
  )

  // nexarq.runReview — run the CLI and update state
  context.subscriptions.push(
    vscode.commands.registerCommand('nexarq.runReview', async () => {
      const workspaceFolders = vscode.workspace.workspaceFolders
      if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('Nexarq: No workspace folder open.')
        return
      }

      const config = vscode.workspace.getConfiguration('nexarq')
      const cliPath = config.get<string>('cliPath') ?? 'nexarq'
      const mode = config.get<string>('mode') ?? 'smart'
      const workingDirectory = workspaceFolders[0]!.uri.fsPath

      const panel = ReviewPanel.show()
      panel.setLoading()

      try {
        const run = await runNexarqCli({ cliPath, workingDirectory, mode })
        reviewState.set(run)
        panel.setRun(run)
      } catch (runError) {
        const message = runError instanceof Error ? runError.message : String(runError)
        panel.setError(message)
        vscode.window.showErrorMessage(`Nexarq review failed: ${message}`)
      }
    })
  )

  // nexarq.showPanel — reveal the panel without re-running
  context.subscriptions.push(
    vscode.commands.registerCommand('nexarq.showPanel', () => {
      const panel = ReviewPanel.show()
      const run = reviewState.get()
      if (run) panel.setRun(run)
    })
  )

  // nexarq.clearDecorations — remove all inline hints
  context.subscriptions.push(
    vscode.commands.registerCommand('nexarq.clearDecorations', () => {
      reviewState.set(null)
    })
  )

  // Auto-run on save if configured
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(() => {
      const config = vscode.workspace.getConfiguration('nexarq')
      if (config.get<boolean>('autoRunOnSave')) {
        vscode.commands.executeCommand('nexarq.runReview')
      }
    })
  )
}

export function deactivate(): void {
  reviewState.set(null)
}
