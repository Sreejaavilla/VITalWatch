"""/api/users. OWNER: Caleb. Admin only.

PHASE 0 PLACEHOLDER — no role check yet. Caleb adds Depends(require("users", "read")).
Acceptance: any non-admin role must get 403 here.
"""

from fastapi import APIRouter

from contracts.models import User
from ...stubs import loader

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[User], summary="List users (admin only)")
def list_users() -> list[User]:
    return [User(**u) for u in loader.load("users")]
