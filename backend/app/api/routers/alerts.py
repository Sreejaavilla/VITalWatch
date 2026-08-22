"""/api/alerts. OWNER: Kavin."""


def list_alerts(user):
    """GET /api/alerts -> Alert[], severity-ranked, each with a deep link."""
    raise NotImplementedError


def acknowledge_alert(alert_id, user):
    """POST /api/alerts/{id}/ack. Writes an audit event. Regulator gets 403."""
    raise NotImplementedError
