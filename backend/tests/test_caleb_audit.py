"""Audit chain tests. OWNER: Caleb.

  * appending N events then verify() -> (True, None)
  * mutating event k out of band then verify() -> (False, k)
  * every mutating endpoint produces exactly one audit event with before AND after
"""
