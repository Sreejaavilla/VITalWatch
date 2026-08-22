"""/auth. OWNER: Caleb."""


def login(email, password):
    """POST /auth/login -> {access_token, role}. Supabase issues the JWT."""
    raise NotImplementedError


def me(user):
    """GET /auth/me -> User, decoded from the bearer token."""
    raise NotImplementedError
