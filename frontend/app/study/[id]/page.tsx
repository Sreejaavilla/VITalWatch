// Study drill-down. OWNER: Ishan.
// Phase 0 placeholder so the dynamic route resolves and the build passes.
// Backing endpoints: GET /api/studies/{id} · GET /api/kpi/study/{id}
//                    GET /api/enrolment/{id} · GET /api/sites?study_id={id}

export default async function StudyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return (
    <main style={{ padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <h1>Study {id}</h1>
      <p style={{ color: '#666' }}>Placeholder — Phase 1.</p>
    </main>
  )
}
