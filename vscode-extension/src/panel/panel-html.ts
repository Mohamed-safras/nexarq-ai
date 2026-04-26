import type { ReviewRun, AgentFinding } from '@nexarq/common/interfaces'
import { escapeHtml } from '../utils/html'
import { SEVERITY_DISPLAY_ORDER, SEVERITY_BADGE_BACKGROUND, SEVERITY_BADGE_TEXT } from '../utils/severity'

export function buildLoadingHtml(): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); background: var(--vscode-editor-background); display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
    .loader { text-align: center; opacity: 0.6; }
    .spinner { width: 32px; height: 32px; border: 3px solid var(--vscode-foreground); border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 12px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="loader">
    <div class="spinner"></div>
    <p>Running Nexarq review…</p>
  </div>
</body>
</html>`
}

export function buildErrorHtml(errorMessage: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); background: var(--vscode-editor-background); padding: 24px; }
    .error-title { color: #f87171; margin-bottom: 8px; }
  </style>
</head>
<body>
  <h2 class="error-title">Review failed</h2>
  <pre>${escapeHtml(errorMessage)}</pre>
</body>
</html>`
}

export function buildReviewHtml(run: ReviewRun): string {
  const elapsed = (run.durationMs / 1000).toFixed(1)
  const ranAt = new Date(run.ranAt).toLocaleTimeString()
  const totalFindings = run.summary.totalFindings

  const findingsByFile = groupFindingsBySeverityThenFile(run)

  const sectionsHtml = SEVERITY_DISPLAY_ORDER
    .filter((severity) => run.summary[severity] > 0)
    .map((severity) => buildSectionHtml(severity, findingsByFile.get(severity) ?? []))
    .join('')

  const emptyStateHtml = totalFindings === 0
    ? '<div class="empty-state">✓ No findings — looking good!</div>'
    : ''

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    * { box-sizing: border-box; }
    body { font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); color: var(--vscode-foreground); background: var(--vscode-editor-background); margin: 0; padding: 0; }
    .header { padding: 16px 20px 12px; border-bottom: 1px solid var(--vscode-panel-border); }
    .header h1 { margin: 0 0 4px; font-size: 15px; font-weight: 600; }
    .meta { font-size: 12px; opacity: 0.6; }
    .section-title { padding: 10px 20px 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.7; border-bottom: 1px solid var(--vscode-panel-border); }
    .finding { padding: 10px 20px; border-bottom: 1px solid var(--vscode-panel-border); cursor: pointer; }
    .finding:hover { background: var(--vscode-list-hoverBackground); }
    .finding-header { display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px; }
    .badge { font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 3px; }
    .file-ref { font-size: 12px; font-family: var(--vscode-editor-font-family); opacity: 0.8; }
    .agent-label { font-size: 11px; opacity: 0.5; }
    .message { font-size: 13px; line-height: 1.4; }
    .suggestion { margin-top: 4px; font-size: 12px; opacity: 0.7; font-style: italic; }
    .empty-state { padding: 48px 20px; text-align: center; opacity: 0.5; font-size: 14px; }
  </style>
</head>
<body>
  <div class="header">
    <h1>Nexarq Review</h1>
    <div class="meta">${totalFindings} finding${totalFindings !== 1 ? 's' : ''}  ·  ${run.summary.agentsRun.length} agents  ·  ${elapsed}s  ·  ${ranAt}</div>
  </div>
  ${emptyStateHtml}
  ${sectionsHtml}
  <script>
    const vscode = acquireVsCodeApi();
    document.querySelectorAll('.finding[data-file]').forEach(el => {
      el.addEventListener('click', () => {
        vscode.postMessage({ command: 'openFile', file: el.dataset.file, line: parseInt(el.dataset.line || '1') });
      });
    });
  </script>
</body>
</html>`
}

function buildSectionHtml(severity: string, findings: AgentFinding[]): string {
  const badgeBackground = SEVERITY_BADGE_BACKGROUND[severity] ?? '#f3f4f6'
  const badgeColor = SEVERITY_BADGE_TEXT[severity] ?? '#374151'

  const findingsHtml = findings.map((finding) => `
  <div class="finding" data-file="${escapeHtml(finding.file ?? '')}" data-line="${finding.line ?? 1}">
    <div class="finding-header">
      <span class="badge" style="background:${badgeBackground};color:${badgeColor}">${severity.toUpperCase()}</span>
      <span class="file-ref">${escapeHtml(finding.file ?? '')}:${finding.line ?? ''}</span>
    </div>
    <div class="message">${escapeHtml(finding.message)}</div>
    ${finding.suggestion ? `<div class="suggestion">Fix: ${escapeHtml(finding.suggestion)}</div>` : ''}
  </div>`).join('')

  return `
  <div class="section-title">${severity}  (${findings.length})</div>
  ${findingsHtml}`
}

function groupFindingsBySeverityThenFile(run: ReviewRun): Map<string, AgentFinding[]> {
  const grouped = new Map<string, AgentFinding[]>()
  for (const result of run.results) {
    for (const finding of result.findings) {
      const severity = finding.severity ?? 'info'
      const existing = grouped.get(severity) ?? []
      existing.push(finding)
      grouped.set(severity, existing)
    }
  }
  return grouped
}
