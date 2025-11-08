import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Insurance Agent Copilot',
  description: 'AI-powered insurance agent assistant',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

