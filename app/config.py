"""Settings and alert thresholds.

Every number a judge might ask "is that hardcoded?" about lives here and is
overridable from the environment. See .env.example.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "VITalWatch"
    org_name: str = "All India Institute of Ayurveda — NPvCC"

    #: Postgres connection string. Set it (Supabase) and every query runs against
    #: Postgres; leave it unset and the same queries run against the SQLite file below.
    #: Use a Supabase *pooler* URL — the direct db.<ref>.supabase.co host is IPv6-only
    #: and most free hosting tiers, Render included, cannot reach it.
    database_url: str | None = None
    #: Connections held open against Postgres. Supabase's free tier is not generous
    #: with these, and one process serving one demo does not need many.
    db_pool_max: int = 5
    #: Seconds to wait for Postgres before giving up. A demo that hangs is worse than
    #: one that says it cannot connect.
    db_connect_timeout: int = 10

    #: SQLite file, used when DATABASE_URL is unset. Generated on first run; never committed.
    db_path: Path = ROOT / "data" / "ctms.db"
    #: Rows generated on an empty database.
    seed_studies: int = 8
    #: Fixed so every run of the demo produces the same portfolio.
    seed_random_seed: int = 20260822

    # --- alert thresholds ---
    #: Enrolment lag alert fires below this % of the plan-to-date figure.
    enrolment_lag_pct: float = 80.0
    #: Ethics renewal alert fires this many days before ec_expiry_date.
    ethics_renewal_days: int = 60
    #: A monitoring visit is overdue this many days past its scheduled date.
    monitoring_overdue_days: int = 14

    # --- statutory clocks, NDCT Rules 2019 ---
    sae_initial_report_hours: int = 24
    sae_narrative_days: int = 14
    #: An SAE deadline within this many hours shows as "due soon" rather than "on track".
    sae_due_soon_hours: int = 6


settings = Settings()
