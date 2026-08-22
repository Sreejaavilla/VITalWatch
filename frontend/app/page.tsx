// Deploy smoke test. OWNER: Kavin (Phase 0) -> Ishan replaces with the real landing page.
// Phase 0 acceptance: the DEPLOYED Vercel page prints the DEPLOYED Render /health JSON.
// If this renders, CORS is configured and the two halves can talk. That is the whole point.

// force-dynamic: must hit the live backend on every request, not at build time.
// Without this the page prerenders and the CORS check proves nothing.
export const dynamic = 'force-dynamic'

async function getHealth() {
  const base = process.env.NEXT_PUBLIC_API_URL
  if (!base) return { error: 'NEXT_PUBLIC_API_URL is not set' }
  try {
    const res = await fetch(`${base}/health`, { cache: 'no-store' })
    return await res.json()
  } catch (e) {
    return { error: String(e) }
  }
}

export default async function Page() {
  const health = await getHealth()
  return (
    <main style={{ fontFamily: 'ui-monospace, monospace', padding: 32 }}>
      <h1>VITalWatch — backend connectivity</h1>
      <pre>{JSON.stringify(health, null, 2)}</pre>
      <p>Demo system · synthetic data only · no real patient data</p>
    </main>
  )
}
