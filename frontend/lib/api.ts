// Single API client. OWNER: Ishan.
// The ONE place that knows whether we're hitting the backend or reading mocks/.
// No component may fetch directly — that is what keeps stub mode working, and stub
// mode is the demo's parachute.

// const STUB = process.env.NEXT_PUBLIC_STUB_MODE === 'true'
// const BASE  = process.env.NEXT_PUBLIC_API_URL

export async function apiGet<T>(path: string): Promise<T> {
  throw new Error('not implemented')
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  throw new Error('not implemented')
}

export async function login(email: string, password: string) {
  throw new Error('not implemented')
}

export function getRole(): string | null {
  // decode the stored JWT's role claim — drives every conditional render
  throw new Error('not implemented')
}
