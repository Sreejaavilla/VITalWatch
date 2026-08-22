"""/api/studies. OWNER: Kavin."""

# router = APIRouter(prefix="/api/studies", tags=["studies"])


def list_studies(user):
    """GET /api/studies -> Study[]. Scoped by role: PI sees own, regulator sees all."""
    raise NotImplementedError


def get_study(study_id, user):
    """GET /api/studies/{id} -> Study. 404 if outside the caller's scope, not 403."""
    raise NotImplementedError
