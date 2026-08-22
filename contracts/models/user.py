"""User and Role. OWNER: Kavin (shape) / Caleb (auth semantics).

Role is the enum every RBAC check in the system resolves against; it must match
the keys in contracts/roles.yaml exactly.
"""

# Role: principal_investigator | study_coordinator | monitor | ethics_committee
#       | pharmacovigilance | admin | regulator
# User fields: id, email, role, full_name, site_ids, study_ids
