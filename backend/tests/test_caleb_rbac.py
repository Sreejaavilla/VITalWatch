"""RBAC matrix tests. OWNER: Caleb. These are the tests a judge would want to see.

Table test: all 7 roles x 9 routers -> assert the status code roles.yaml predicts.
Named cases that must pass before the Phase 1 gate:
  * study_coordinator token -> 403 on GET /api/export/sdtm
  * regulator token         -> 200 on GET /api/export/sdtm
  * regulator token         -> 403 on every POST/PATCH/DELETE in the app
  * any role                -> no name field anywhere in a subject response
"""
