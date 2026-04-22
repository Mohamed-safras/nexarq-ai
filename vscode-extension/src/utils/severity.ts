import type { Severity } from '@nexarq/common/types'

export const SEVERITY_DISPLAY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'info']

export const SEVERITY_DECORATION_COLOR: Record<string, string> = {
  critical: '#f87171',
  high:     '#fb923c',
  medium:   '#fbbf24',
  low:      '#60a5fa',
  info:     '#9ca3af',
}

export const SEVERITY_BADGE_BACKGROUND: Record<string, string> = {
  critical: '#fee2e2',
  high:     '#ffedd5',
  medium:   '#fef9c3',
  low:      '#dbeafe',
  info:     '#f3f4f6',
}

export const SEVERITY_BADGE_TEXT: Record<string, string> = {
  critical: '#991b1b',
  high:     '#9a3412',
  medium:   '#854d0e',
  low:      '#1e40af',
  info:     '#374151',
}
