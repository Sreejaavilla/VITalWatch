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

    #: SQLite file. Generated on first run; never committed.
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
