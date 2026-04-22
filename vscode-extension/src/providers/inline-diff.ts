import * as vscode from 'vscode'
import type { AgentFinding } from '@nexarq/common/interfaces'
import { reviewState } from '../state'
import { SEVERITY_BADGE_BACKGROUND, SEVERITY_BADGE_TEXT } from '../utils/severity'

export class InlineDiffController implements vscode.Disposable {
  private readonly findingDecorationType: vscode.TextEditorDecorationType

  constructor() {
    this.findingDecorationType = vscode.window.createTextEditorDecorationType({
      overviewRulerLane: vscode.OverviewRulerLane.Right,
      overviewRulerColor: new vscode.ThemeColor('editorWarning.foreground'),
    })
  }

  applyToEditor(editor: vscode.TextEditor): void {
    const run = reviewState.get()
    if (!run) return

    const relativePath = vscode.workspace.asRelativePath(editor.document.uri, false)
    const findings = run.results
      .flatMap((result) => result.findings)
      .filter((finding) => finding.file === relativePath && finding.suggestion)

    const decorations: vscode.DecorationOptions[] = findings.map((finding) =>
      buildDecoration(finding)
    )

    editor.setDecorations(this.findingDecorationType, decorations)
  }

  clear(): void {
    for (const editor of vscode.window.visibleTextEditors) {
      editor.setDecorations(this.findingDecorationType, [])
    }
  }

  dispose(): void {
    this.findingDecorationType.dispose()
  }
}

function buildDecoration(finding: AgentFinding): vscode.DecorationOptions {
  const lineIndex = Math.max(0, (finding.line ?? 1) - 1)
  const severity = String(finding.severity ?? 'info')

  return {
    range: new vscode.Range(lineIndex, 0, lineIndex, 0),
    hoverMessage: buildHoverMessage(finding),
    renderOptions: {
      after: {
        contentText: `  ${finding.suggestion}`,
        color: SEVERITY_BADGE_TEXT[severity] ?? '#374151',
        backgroundColor: SEVERITY_BADGE_BACKGROUND[severity] ?? '#f3f4f6',
        fontStyle: 'italic',
        margin: '0 0 0 2em',
      },
    },
  }
}

function buildHoverMessage(finding: AgentFinding): vscode.MarkdownString {
  const markdown = new vscode.MarkdownString('', true)
  markdown.isTrusted = true
  markdown.appendMarkdown(`**${String(finding.severity ?? 'info').toUpperCase()}** — ${finding.message}`)
  if (finding.suggestion) {
    markdown.appendMarkdown(`\n\n**Suggested fix:** ${finding.suggestion}`)
  }
  return markdown
}
