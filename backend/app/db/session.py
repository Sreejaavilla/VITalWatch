"""Supabase/Postgres connection. OWNER: Caleb.

Must be import-safe when STUB_MODE=true — importing this file with no DATABASE_URL
set may not raise, or stub mode breaks for everyone.
"""


def get_connection():
    """Yield a connection. Raise a clear error if called while STUB_MODE=true."""
    raise NotImplementedError
