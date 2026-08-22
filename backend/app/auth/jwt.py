"""Supabase JWT verification. OWNER: Caleb."""


def decode_token(token):
    """Verify signature against SUPABASE_JWT_SECRET, return claims. Raise 401 otherwise."""
    raise NotImplementedError


def current_user(authorization_header):
    """FastAPI dependency -> User. 401 if missing or invalid."""
    raise NotImplementedError
