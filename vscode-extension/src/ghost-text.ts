import * as vscode from 'vscode'
import type { ParsedFinding } from './types.ts'

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#f87171',
  high:     '#fb923c',
  medium:   '#fbbf24',
  low:      '#60a5fa',
  info:     '#9ca3af',
}

export class GhostTextController {
  private readonly decorationTypes: Map<string, vscode.TextEditorDecorationType> = new Map()

  constructor() {
    for (const [severity, color] of Object.entries(SEVERITY_COLORS)) {
      this.decorationTypes.set(
        severity,
        vscode.window.createTextEditorDecorationType({
          after: {
            color,
            fontStyle: 'italic',
            margin: '0 0 0 2em',
          },
          isWholeLine: false,
        })
      )
    }
  }

  applyFindings(findings: ParsedFinding[]): void {
    const editors = vscode.window.visibleTextEditors
    this.clearAll(editors)

    const findingsByFile = groupByFile(findings)

    for (const editor of editors) {
      const filePath = vscode.workspace.asRelativePath(editor.document.uri, false)
      const fileFindings = findingsByFile.get(filePath) ?? []
      this.applyToEditor(editor, fileFindings)
    }
  }

  applyToEditor(editor: vscode.TextEditor, findings: ParsedFinding[]): void {
    const decorationsByType = new Map<string, vscode.DecorationOptions[]>()

    for (const finding of findings) {
      const lineIndex = Math.max(0, finding.line - 1)
      if (lineIndex >= editor.document.lineCount) continue

      const lineLength = editor.document.lineAt(lineIndex).text.length
      const range = new vscode.Range(lineIndex, lineLength, lineIndex, lineLength)

      const truncatedMessage = finding.message.length > 60
        ? finding.message.slice(0, 57) + '…'
        : finding.message

      const decorationOptions: vscode.DecorationOptions = {
        range,
        renderOptions: {
          after: { contentText: `  ⚠ [${finding.agentName}] ${truncatedMessage}` },
        },
      }

      const existing = decorationsByType.get(finding.severity) ?? []
      existing.push(decorationOptions)
      decorationsByType.set(finding.severity, existing)
    }

    for (const [severity, decorationType] of this.decorationTypes) {
      editor.setDecorations(decorationType, decorationsByType.get(severity) ?? [])
    }
  }

  clearAll(editors: readonly vscode.TextEditor[]): void {
    for (const editor of editors) {
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

function groupByFile(findings: ParsedFinding[]): Map<string, ParsedFinding[]> {
  const result = new Map<string, ParsedFinding[]>()
  for (const finding of findings) {
    const existing = result.get(finding.file) ?? []
    existing.push(finding)
    result.set(finding.file, existing)
  }
  return result
}
