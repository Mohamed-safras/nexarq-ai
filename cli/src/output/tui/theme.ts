export type ThemeVariant =
  | 'dark'
  | 'light'
  | 'dark-colorblind'
  | 'light-colorblind'
  | 'dark-ansi'
  | 'light-ansi'

export interface NexarqTheme {
  bg: string
  bgPanel: string
  bgAlt: string
  fg: string
  fgDim: string
  cyan: string
  green: string
  yellow: string
  red: string
  orange: string
  purple: string
  severity: {
    critical: string
    high: string
    medium: string
    low: string
    info: string
  }
}

// ── Tokyo Night (default) ────────────────────────────────────────────────────
const dark: NexarqTheme = {
  bg:      '#1a1b26',
  bgPanel: '#16161e',
  bgAlt:   '#24283b',
  fg:    '#c0caf5',
  fgDim: '#565f89',
  cyan:   '#7dcfff',
  green:  '#9ece6a',
  yellow: '#e0af68',
  red:    '#f7768e',
  orange: '#ff9e64',
  purple: '#bb9af7',
  severity: {
    critical: '#f7768e',
    high:     '#ff9e64',
    medium:   '#e0af68',
    low:      '#7dcfff',
    info:     '#565f89',
  },
}

// ── Light (GitHub-style) ─────────────────────────────────────────────────────
const light: NexarqTheme = {
  bg:      '#ffffff',
  bgPanel: '#f6f8fa',
  bgAlt:   '#eaeef2',
  fg:    '#24292f',
  fgDim: '#6e7781',
  cyan:   '#0969da',
  green:  '#1a7f37',
  yellow: '#9a6700',
  red:    '#cf222e',
  orange: '#bc4c00',
  purple: '#8250df',
  severity: {
    critical: '#cf222e',
    high:     '#bc4c00',
    medium:   '#9a6700',
    low:      '#0969da',
    info:     '#6e7781',
  },
}

// ── Dark colorblind-friendly (Okabe-Ito palette) ─────────────────────────────
const darkColorblind: NexarqTheme = {
  bg:      '#1a1b26',
  bgPanel: '#16161e',
  bgAlt:   '#24283b',
  fg:    '#c0caf5',
  fgDim: '#565f89',
  cyan:   '#56b4e9',
  green:  '#f0e442',   // yellow instead of green for deuteranopia
  yellow: '#e69f00',
  red:    '#d55e00',   // orange-red, distinguishable from green
  orange: '#cc79a7',
  purple: '#0072b2',
  severity: {
    critical: '#d55e00',
    high:     '#cc79a7',
    medium:   '#e69f00',
    low:      '#56b4e9',
    info:     '#565f89',
  },
}

// ── Light colorblind-friendly ────────────────────────────────────────────────
const lightColorblind: NexarqTheme = {
  bg:      '#ffffff',
  bgPanel: '#f6f8fa',
  bgAlt:   '#eaeef2',
  fg:    '#24292f',
  fgDim: '#6e7781',
  cyan:   '#0072b2',
  green:  '#f0e442',
  yellow: '#e69f00',
  red:    '#d55e00',
  orange: '#cc79a7',
  purple: '#cc79a7',
  severity: {
    critical: '#d55e00',
    high:     '#cc79a7',
    medium:   '#e69f00',
    low:      '#0072b2',
    info:     '#6e7781',
  },
}

// ── Dark ANSI (16-color safe) ────────────────────────────────────────────────
const darkAnsi: NexarqTheme = {
  bg:      '#000000',
  bgPanel: '#111111',
  bgAlt:   '#222222',
  fg:    '#ffffff',
  fgDim: '#888888',
  cyan:   '#00ffff',
  green:  '#00ff00',
  yellow: '#ffff00',
  red:    '#ff0000',
  orange: '#ff8800',
  purple: '#ff00ff',
  severity: {
    critical: '#ff0000',
    high:     '#ff8800',
    medium:   '#ffff00',
    low:      '#00ffff',
    info:     '#888888',
  },
}

// ── Light ANSI ───────────────────────────────────────────────────────────────
const lightAnsi: NexarqTheme = {
  bg:      '#ffffff',
  bgPanel: '#eeeeee',
  bgAlt:   '#dddddd',
  fg:    '#000000',
  fgDim: '#666666',
  cyan:   '#0000cc',
  green:  '#006600',
  yellow: '#886600',
  red:    '#cc0000',
  orange: '#994400',
  purple: '#660099',
  severity: {
    critical: '#cc0000',
    high:     '#994400',
    medium:   '#886600',
    low:      '#0000cc',
    info:     '#666666',
  },
}

export const THEME_VARIANTS: Record<ThemeVariant, NexarqTheme> = {
  'dark':             dark,
  'light':            light,
  'dark-colorblind':  darkColorblind,
  'light-colorblind': lightColorblind,
  'dark-ansi':        darkAnsi,
  'light-ansi':       lightAnsi,
}

export const THEME_LABELS: Record<ThemeVariant, string> = {
  'dark':             'Dark mode',
  'light':            'Light mode',
  'dark-colorblind':  'Dark mode (colorblind-friendly)',
  'light-colorblind': 'Light mode (colorblind-friendly)',
  'dark-ansi':        'Dark mode (ANSI colors only)',
  'light-ansi':       'Light mode (ANSI colors only)',
}

export function getThemeByVariant(variant: ThemeVariant): NexarqTheme {
  return THEME_VARIANTS[variant]
}

// Default export — dark theme. Import this in all commands.
export const THEME: NexarqTheme = dark

export type SeverityKey = keyof NexarqTheme['severity']
