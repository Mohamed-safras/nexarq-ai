import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Nexarq — Free AI Code Review',
  description: 'multi-agent code review. Free and open-source.',
  openGraph: {
    title: 'Nexarq — Free AI Code Review',
    description: 'multi-agent code review. Free and open-source.',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-zinc-950 text-zinc-100 antialiased">{children}</body>
    </html>
  )
}
