"""User and Role. OWNER: Kavin (shape) / Caleb (auth semantics).

Role is the enum every RBAC check resolves against. The values here MUST match the
keys in contracts/roles.yaml exactly — a mismatch is a silent 403 storm.
"""

from enum import Enum

from .common import CTMSModel


class Role(str, Enum):
    PRINCIPAL_INVESTIGATOR = "principal_investigator"
    STUDY_COORDINATOR = "study_coordinator"
    MONITOR = "monitor"
    ETHICS_COMMITTEE = "ethics_committee"
    PHARMACOVIGILANCE = "pharmacovigilance"
    ADMIN = "admin"
    REGULATOR = "regulator"


#: Roles that may never mutate anything, on any endpoint. Enforced in auth/rbac.py.
READ_ONLY_ROLES = frozenset({Role.REGULATOR})


class User(CTMSModel):
    id: str
    email: str
    full_name: str
    role: Role
    #: Scope: which studies/sites this user may see. Empty list = all (admin, regulator, EC).
    study_ids: list[str] = []
    site_ids: list[str] = []
    active: bool = True
