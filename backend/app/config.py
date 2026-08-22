"""Settings and the STUB_MODE flag. OWNER: Kavin.

STUB_MODE=true must run the entire API from contracts/fixtures/ with no database,
no Supabase and no ML model. This is what Ishan develops against and what saves
the demo if something dies on stage.
"""

# class Settings(BaseSettings):
#     stub_mode: bool = True
#     supabase_url: str | None = None
#     supabase_jwt_secret: str | None = None
#     database_url: str | None = None
#     cors_origins: str = "http://localhost:3000"
#     alert_enrolment_lag_pct: int = 80
#     alert_ethics_renewal_days: int = 30
#     alert_monitoring_visit_grace_days: int = 7


def get_settings():
    """Cached settings singleton."""
    raise NotImplementedError
