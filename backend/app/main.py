"""FastAPI entrypoint. OWNER: Kavin.

Written at hour 0 and NOT TOUCHED AGAIN. Every router is registered here before it
exists, so no two people ever edit the same file. If you need a new route, add it to
YOUR router file — not here.
"""

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from .config import settings
# from .api.routers import (
#     studies, sites, enrolment, kpi, alerts,      # Kavin
#     auth, users, audit,                          # Caleb
#     ae, signals,                                 # Sreeja
#     export, fhir,                                # Roxy
# )


def create_app():
    """Build the app, mount CORS, register all routers."""
    raise NotImplementedError


def health():
    """GET /health -> {"status": "ok", "stub_mode": bool}. First thing deployed."""
    raise NotImplementedError


# app = create_app()
