"""AuditEvent — append-only, hash-chained. OWNER: Kavin (shape) / Caleb (writer).

ALCOA+: attributable, legible, contemporaneous, original, accurate.
Nothing in this model is ever mutable after write.
"""

# Fields: id, seq, actor_id, actor_role, action, resource_type, resource_id,
#   before (json|null), after (json|null), timestamp_utc, prev_hash, hash, reason
