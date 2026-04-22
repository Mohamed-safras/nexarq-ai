import * as vscode from 'vscode'
import type { ReviewRun, AgentFinding } from '@nexarq/common/interfaces'
import { SEVERITY_DECORATION_COLOR } from '../utils/severity'

export class GhostTextController implements vscode.Disposable {
  private readonly decorationTypes: Map<string, vscode.TextEditorDecorationType>

  constructor() {
    this.decorationTypes = new Map(
      Object.entries(SEVERITY_DECORATION_COLOR).map(([severity, color]) => [
        severity,
        vscode.window.createTextEditorDecorationType({
          after: { color, fontStyle: 'italic', margin: '0 0 0 2em' },
          isWholeLine: false,
        }),
      ])
    )
  }

  applyRun(run: ReviewRun): void {
    const findingsByFile = groupFindingsByFile(run)
    for (const editor of vscode.window.visibleTextEditors) {
      const relativePath = vscode.workspace.asRelativePath(editor.document.uri, false)
      this.applyToEditor(editor, findingsByFile.get(relativePath) ?? [])
    }
  }

  applyToEditor(editor: vscode.TextEditor, findings: AgentFinding[]): void {
    const decorationsByType = new Map<string, vscode.DecorationOptions[]>()

    for (const finding of findings) {
      const lineIndex = Math.max(0, (finding.line ?? 1) - 1)
      if (lineIndex >= editor.document.lineCount) continue

      const lineEnd = editor.document.lineAt(lineIndex).text.length
      const range = new vscode.Range(lineIndex, lineEnd, lineIndex, lineEnd)
      const severity = String(finding.severity ?? 'info')
      const truncatedMessage = finding.message.length > 60
        ? finding.message.slice(0, 57) + '…'
        : finding.message

      const existing = decorationsByType.get(severity) ?? []
      existing.push({ range, renderOptions: { after: { contentText: `  ⚠ ${truncatedMessage}` } } })
      decorationsByType.set(severity, existing)
    }

    for (const [severity, decorationType] of this.decorationTypes) {
      editor.setDecorations(decorationType, decorationsByType.get(severity) ?? [])
    }
  }

  clear(): void {
    for (const editor of vscode.window.visibleTextEditors) {
      for (const decorationType of this.decorationTypes.values()) {
        editor.setDecorations(decorationType, [])
      }
    }
  }

  dispose(): void {
    for (const decorationType of this.decorationTypes.values()) {
      decorationType.dispose()
    }
    this.decorationTypes.clear()
  }
}

function groupFindingsByFile(run: ReviewRun): Map<string, AgentFinding[]> {
  const result = new Map<string, AgentFinding[]>()
  for (const agentResult of run.results) {
    for (const finding of agentResult.findings) {
      const filePath = finding.file ?? ''
      const existing = result.get(filePath) ?? []
      existing.push(finding)
      result.set(filePath, existing)
    }
  }
  return result
}
