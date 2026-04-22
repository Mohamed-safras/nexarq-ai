import * as vscode from 'vscode'
import type { ReviewRun } from '@nexarq/common/interfaces'
import { buildLoadingHtml, buildErrorHtml, buildReviewHtml } from './panel-html'

export class ReviewPanel {
  private static instance: ReviewPanel | undefined
  private readonly webviewPanel: vscode.WebviewPanel

  private constructor(webviewPanel: vscode.WebviewPanel) {
    this.webviewPanel = webviewPanel
    this.webviewPanel.onDidDispose(() => {
      ReviewPanel.instance = undefined
    })
  }

  static show(): ReviewPanel {
    if (ReviewPanel.instance) {
      ReviewPanel.instance.webviewPanel.reveal()
      return ReviewPanel.instance
    }

    const webviewPanel = vscode.window.createWebviewPanel(
      'nexarqReview',
      'Nexarq Review',
      vscode.ViewColumn.Two,
      { enableScripts: true, retainContextWhenHidden: true }
    )

    ReviewPanel.instance = new ReviewPanel(webviewPanel)
    ReviewPanel.instance.setLoading()
    return ReviewPanel.instance
  }

  setLoading(): void {
    this.webviewPanel.webview.html = buildLoadingHtml()
  }

  setRun(run: ReviewRun): void {
    this.webviewPanel.webview.html = buildReviewHtml(run)
    this.webviewPanel.webview.onDidReceiveMessage(
      (message: { command: string; file?: string; line?: number }) => {
        if (message.command === 'openFile' && message.file) {
          this.openFileAtLine(message.file, message.line ?? 1)
        }
      }
    )
  }

  setError(errorMessage: string): void {
    this.webviewPanel.webview.html = buildErrorHtml(errorMessage)
  }

  private async openFileAtLine(filePath: string, lineNumber: number): Promise<void> {
    const workspaceFolders = vscode.workspace.workspaceFolders
    if (!workspaceFolders || workspaceFolders.length === 0) return

    const fileUri = vscode.Uri.joinPath(workspaceFolders[0]!.uri, filePath)
    try {
      const document = await vscode.workspace.openTextDocument(fileUri)
      const editor = await vscode.window.showTextDocument(document, vscode.ViewColumn.One)
      const targetLine = Math.max(0, lineNumber - 1)
      const position = new vscode.Position(targetLine, 0)
      editor.selection = new vscode.Selection(position, position)
      editor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenter)
    } catch {
      vscode.window.showWarningMessage(`Could not open: ${filePath}`)
    }
  }
}
