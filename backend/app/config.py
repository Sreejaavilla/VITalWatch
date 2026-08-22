"""Settings and the STUB_MODE flag. OWNER: Kavin.

STUB_MODE=true must run the entire API from contracts/fixtures/ with no database,
no Supabase and no ML model. It is what Ishan develops against and the parachute if
something dies on stage — so nothing in this file may require a secret to import.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    stub_mode: bool = True

    # --- Supabase (Caleb) --- all optional: unset must not break stub mode
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None
    database_url: str | None = None

    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    audit_chain_seed: str = "vitalwatch-genesis"

    # --- alert thresholds (Kavin) --- change one, refresh, the dashboard changes
    alert_enrolment_lag_pct: int = 80
    alert_ethics_renewal_days: int = 30
    alert_monitoring_visit_grace_days: int = 7

    # --- pharmacovigilance (Sreeja) ---
    pv_coding_backend: str = "mock"
    pv_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    pv_embeddings_path: str = "services/pv/coding/embeddings.npy"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
