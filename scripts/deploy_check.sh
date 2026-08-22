#!/usr/bin/env bash
# Pre-flight against a deployed instance, or against localhost.
#
#   ./scripts/deploy_check.sh                       # local
#   ./scripts/deploy_check.sh https://your.app      # deployed, also warms a cold start
#
# Run this before the demo. A free-tier instance cold-starts slowly, and the first
# request should be this script's rather than a judge watching a spinner.
set -euo pipefail
BASE="${1:-http://localhost:8000}"

echo "checking ${BASE}"
fail=0
for path in /health /portfolio /study/STU-004 /ae /signals /audit \
            /role/investigator /role/safety /role/leadership \
            /api/kpi/portfolio /api/kpi/role/leadership /api/alerts /api/signals \
            /api/audit/verify /api/fhir/ResearchStudy/STU-001 \
            /api/export/sdtm/dm.csv /docs; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 60 "${BASE}${path}")
    if [ "$code" = "200" ]; then
        printf '  ok   %s\n' "$path"
    else
        printf '  FAIL %s -> %s\n' "$path" "$code"
        fail=1
    fi
done

echo
echo "audit chain:"
curl -s --max-time 30 "${BASE}/api/audit/verify"
echo
exit $fail
