"""Hardcoded Phase 0 seed. OWNER: Kavin. TEMPORARY BY DESIGN.

Just enough for every endpoint to return a plausible shape before Roxy's generator
lands. Two studies, two sites, one AE, one alert, one audit event — shapes matter here,
volume does not. Once contracts/fixtures/ exists, none of this is read.
"""

SEED: dict[str, list] = {
    "studies": [
        {
            "id": "STU-001", "title": "Ashwagandha in generalised anxiety disorder",
            "protocol_no": "AIIA/2026/001", "ctri_number": "CTRI/2026/03/012345",
            "phase": "III", "status": "enrolling", "therapeutic_area": "Psychiatry",
            "ec_approval_date": "2026-02-10", "ec_expiry_date": "2026-09-15",
            "ctri_registration_date": "2026-02-28",
            "target_enrolment": 240, "actual_enrolment": 131,
            "pi_id": "USR-002", "site_ids": ["SITE-01", "SITE-04"],
            "start_date": "2026-03-01", "end_date": None,
        },
        {
            "id": "STU-002", "title": "Guggulu formulation in dyslipidaemia",
            "protocol_no": "AIIA/2026/002", "ctri_number": "CTRI/2026/04/012901",
            "phase": "II", "status": "enrolling", "therapeutic_area": "Cardiology",
            "ec_approval_date": "2026-03-05", "ec_expiry_date": "2027-03-04",
            "ctri_registration_date": "2026-04-02",
            "target_enrolment": 120, "actual_enrolment": 38,
            "pi_id": "USR-003", "site_ids": ["SITE-02"],
            "start_date": "2026-04-15", "end_date": None,
        },
    ],
    "sites": [
        {"id": "SITE-01", "name": "AIIA New Delhi", "city": "New Delhi", "state": "Delhi",
         "status": "activated", "activated_date": "2026-03-01", "pi_name": "Dr A Sharma",
         "capacity": 150, "study_ids": ["STU-001"]},
        {"id": "SITE-02", "name": "AIIA Goa Satellite", "city": "Panaji", "state": "Goa",
         "status": "activated", "activated_date": "2026-04-15", "pi_name": "Dr R Naik",
         "capacity": 80, "study_ids": ["STU-002"]},
        {"id": "SITE-04", "name": "Regional Centre Jaipur", "city": "Jaipur", "state": "Rajasthan",
         "status": "planned", "activated_date": None, "pi_name": "Dr M Rathore",
         "capacity": 90, "study_ids": ["STU-001"]},
    ],
    "alerts": [
        {"id": "ALT-001", "rule": "enrolment_lag", "severity": "critical",
         "study_id": "STU-002", "study_title": "Guggulu formulation in dyslipidaemia",
         "message": "Enrolment at 32% of target; plan expects 71% by today.",
         "raised_at": "2026-08-22T04:00:00Z", "deep_link": "/study/STU-002",
         "acknowledged_by": None, "acknowledged_at": None},
        {"id": "ALT-002", "rule": "ethics_renewal_due", "severity": "warning",
         "study_id": "STU-001", "study_title": "Ashwagandha in generalised anxiety disorder",
         "message": "Ethics Committee approval expires in 24 days (2026-09-15).",
         "raised_at": "2026-08-22T04:00:00Z", "deep_link": "/study/STU-001",
         "acknowledged_by": None, "acknowledged_at": None},
    ],
    "adverse_events": [
        {"id": "AE-001", "study_id": "STU-001", "site_id": "SITE-01",
         "subject_code": "AIIA-001-014", "narrative": "Subject reported severe headache and nausea 3 hours after dosing.",
         "onset_date": "2026-08-20", "serious": True, "severity": "severe",
         "causality": "possible", "outcome": "recovering",
         "coded_term": "Headache", "coded_code": "MOCK-10019211", "coding_confidence": 0.91,
         "coding_source": "mock", "suspect_drug": "Ashwagandha churna", "drug_code": "MOCKD-0042",
         "drug_coding_source": "mock", "reported_at": "2026-08-20T11:20:00Z",
         "deadline_24h": "2026-08-21T09:00:00Z", "deadline_14d": "2026-09-03T09:00:00Z",
         "timeline_status": "breached"},
    ],
    "audit_events": [
        {"id": "AUD-001", "seq": 1, "actor_id": "USR-004", "actor_role": "pharmacovigilance",
         "action": "create", "resource_type": "adverse_event", "resource_id": "AE-001",
         "before": None, "after": {"id": "AE-001", "serious": True},
         "timestamp_utc": "2026-08-20T11:20:00Z", "reason": None,
         "prev_hash": "0" * 64, "hash": "seed-not-a-real-hash"},
    ],
    "users": [
        {"id": "USR-001", "email": "pi@aiia.demo", "full_name": "Dr A Sharma",
         "role": "principal_investigator", "study_ids": ["STU-001"], "site_ids": [], "active": True},
        {"id": "USR-004", "email": "pv@aiia.demo", "full_name": "Dr S Iyer",
         "role": "pharmacovigilance", "study_ids": [], "site_ids": [], "active": True},
    ],
    "subjects": [], "visits": [], "deviations": [], "queries": [],
    "milestones": [], "signals": [],
}
