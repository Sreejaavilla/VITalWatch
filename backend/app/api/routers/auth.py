"""/auth. OWNER: Caleb.

PHASE 0 PLACEHOLDER wired by Kavin so main.py registers cleanly and Ishan can build a
login screen today. Caleb replaces the body with real Supabase JWT issuance — the
route shapes below are the contract and should not change.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from contracts.models import Role, User
from ...stubs import loader

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    role: Role
    user: User


@router.post("/login", response_model=LoginResponse, summary="Exchange credentials for a token")
def login(body: LoginRequest) -> LoginResponse:
    """PLACEHOLDER: matches on email only, returns an unsigned token. NOT AUTH.

    Caleb: verify against Supabase, return the real JWT. Must carry a `role` claim.
    """
    record = loader.find("users", "email", body.email)
    if record is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = User(**record)
    return LoginResponse(access_token=f"stub-token-{user.id}", role=user.role, user=user)


@router.get("/me", response_model=User, summary="Current user from the bearer token")
def me() -> User:
    """PLACEHOLDER: returns the first seeded user. Caleb: decode the bearer token."""
    users = loader.load("users")
    if not users:
        raise HTTPException(status_code=401, detail="No authenticated user")
    return User(**users[0])
