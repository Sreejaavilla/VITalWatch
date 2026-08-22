// Root layout. OWNER: Ishan.
// Phase 0: minimal shell so the app builds. Ishan replaces with the real chrome
// (role badge, nav, alert bell) in Phase 1.

import type { ReactNode } from 'react'

export const metadata = {
  title: 'VITalWatch — AIIA CTMS',
  description: 'Clinical trial management and pharmacovigilance for AIIA. Demo system, synthetic data only.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: 'system-ui, sans-serif' }}>{children}</body>
    </html>
  )
}
