// Role constants + default landing screen per role. OWNER: Ishan.
// Must stay in sync with contracts/roles.yaml. This file is presentation only —
// it hides UI, it does not enforce anything. Enforcement is Caleb's, server-side.

export const ROLES = [
  'principal_investigator',
  'study_coordinator',
  'monitor',
  'ethics_committee',
  'pharmacovigilance',
  'admin',
  'regulator',
] as const

export const LANDING: Record<string, string> = {}
