"""FastAPI entrypoint. OWNER: Kavin.

Written at hour 0 and NOT TOUCHED AGAIN. Every router is registered here up front so
no two people ever edit the same file. If you need a new route, add it to YOUR router
module — not here.

  Kavin   studies · sites · enrolment · kpi · alerts
  Caleb   auth · users · audit
  Sreeja  ae · signals
  Roxy    export · fhir
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routers import (
    ae,
    alerts,
    audit,
    auth,
    enrolment,
    export,
    fhir,
    kpi,
    signals,
    sites,
    studies,
    users,
)
from .config import settings
from .stubs import loader

ROUTERS = [
    studies.router, sites.router, enrolment.router, kpi.router, alerts.router,  # Kavin
    auth.router, users.router, audit.router,                                    # Caleb
    ae.router, signals.router,                                                  # Sreeja
    export.router, fhir.router,                                                 # Roxy
]

DESCRIPTION = """
Real-time CTMS and pharmacovigilance dashboard for the All India Institute of Ayurveda.

**Demo system. Synthetic data only. No real patient data at any stage.**

Which endpoint backs which screen (Ishan):

| Screen | Endpoints |
|---|---|
| `/login` | `POST /auth/login`, `GET /auth/me` |
| `/portfolio` | `GET /api/kpi/portfolio`, `GET /api/studies`, `GET /api/alerts` |
| `/study/[id]` | `GET /api/studies/{id}`, `GET /api/kpi/study/{id}`, `GET /api/enrolment/{id}`, `GET /api/sites?study_id=` |
| `/ae` | `POST /api/ae`, `GET /api/ae`, `POST /api/coding/suggest`, `GET /api/signals` |
| `/audit` | `GET /api/audit`, `GET /api/audit/verify` |
| `/alerts` | `GET /api/alerts`, `POST /api/alerts/{id}/ack` |
"""


def create_app() -> FastAPI:
    app = FastAPI(
        title="VITalWatch CTMS API",
        version="0.1.0",
        description=DESCRIPTION,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Caleb, Phase 2: app.add_middleware(AuditMutations) — audits every successful mutation
    for router in ROUTERS:
        app.include_router(router)

    @app.get("/health", tags=["ops"], summary="Liveness + which data source is answering")
    def health() -> dict:
        return {
            "status": "ok",
            "stub_mode": settings.stub_mode,
            "data_source": loader.source_of("studies"),
            "routers": len(ROUTERS),
        }

    return app


app = create_app()
