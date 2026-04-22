import * as vscode from 'vscode'
import type { AgentFinding } from '@nexarq/common/interfaces'
import { reviewState } from '../state'

export class NexarqCodeActionProvider implements vscode.CodeActionProvider {
  static readonly providedCodeActionKinds = [vscode.CodeActionKind.QuickFix]

  provideCodeActions(
    document: vscode.TextDocument,
    range: vscode.Range,
  ): vscode.CodeAction[] {
    const run = reviewState.get()
    if (!run) return []

    const relativePath = vscode.workspace.asRelativePath(document.uri, false)
    const lineNumber = range.start.line + 1

    const matchingFindings = run.results
      .flatMap((result) => result.findings)
      .filter((finding) =>
        finding.file === relativePath &&
        finding.line === lineNumber &&
        finding.suggestion
      )

    return matchingFindings.map((finding) => buildQuickFix(document, range, finding))
  }
}

function buildQuickFix(
  document: vscode.TextDocument,
  range: vscode.Range,
  finding: AgentFinding,
): vscode.CodeAction {
  const action = new vscode.CodeAction(
    `Nexarq: ${finding.suggestion}`,
    vscode.CodeActionKind.QuickFix
  )

  const lineIndex = range.start.line
  const indentation = document.lineAt(lineIndex).text.match(/^(\s*)/)?.[1] ?? ''
  const suggestionLine = `${indentation}nexarq: ${finding.suggestion}\n`

  action.edit = new vscode.WorkspaceEdit()
  action.edit.insert(document.uri, new vscode.Position(lineIndex, 0), suggestionLine)

  // Let VS Code comment the inserted line using the document's own language rules
  action.command = {
    command: 'nexarq.commentInsertedLine',
    title: 'Toggle comment on inserted suggestion',
    arguments: [document.uri, lineIndex],
  }

  action.isPreferred = false
  return action
}
