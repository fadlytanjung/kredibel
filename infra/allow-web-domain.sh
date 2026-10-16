#!/usr/bin/env bash
# Lets the web app run on another domain (a custom domain on Firebase Hosting): adds
# https://<domain>/* to the browser API key's website restrictions (keeping its API targets) and
# <domain> to Firebase Authentication's authorized domains. Prints the lists, never the key.
#   infra/allow-web-domain.sh kredibel.app www.kredibel.app
set -euo pipefail
PROJECT_ID="${PROJECT_ID:-cloud-hack2skill}"
KEY_UID_PREFIX="${KEY_UID_PREFIX:-3a4f39a8}"   # the key the SPA is built with (VITE_FIREBASE_API_KEY)
[ $# -ge 1 ] || { echo "usage: $0 <domain> [<domain>...]" >&2; exit 2; }

TOKEN=$(gcloud auth print-access-token)
HDR=(-H "Authorization: Bearer $TOKEN" -H "x-goog-user-project: $PROJECT_ID" -H "Content-Type: application/json")

NAME=$(gcloud services api-keys list --project="$PROJECT_ID" --format='value(name)' --filter="uid~^$KEY_UID_PREFIX")
[ -n "$NAME" ] || { echo "no API key with uid $KEY_UID_PREFIX..." >&2; exit 1; }
KEY_PATCH=$(curl -s "${HDR[@]}" "https://apikeys.googleapis.com/v2/$NAME" | python3 -c '
import json, sys
r = json.load(sys.stdin)["restrictions"]
refs = r["browserKeyRestrictions"]["allowedReferrers"]
for domain in sys.argv[1:]:
    if f"https://{domain}/*" not in refs:
        refs.append(f"https://{domain}/*")
print(json.dumps({"restrictions": r}))
' "$@")
curl -s -X PATCH "${HDR[@]}" "https://apikeys.googleapis.com/v2/$NAME?updateMask=restrictions" -d "$KEY_PATCH" >/dev/null

AUTH_PATCH=$(curl -s "${HDR[@]}" "https://identitytoolkit.googleapis.com/admin/v2/projects/$PROJECT_ID/config" | python3 -c '
import json, sys
domains = json.load(sys.stdin).get("authorizedDomains", [])
for domain in sys.argv[1:]:
    if domain not in domains:
        domains.append(domain)
print(json.dumps({"authorizedDomains": domains}))
' "$@")
curl -s -X PATCH "${HDR[@]}" "https://identitytoolkit.googleapis.com/admin/v2/projects/$PROJECT_ID/config?updateMask=authorizedDomains" -d "$AUTH_PATCH" >/dev/null

sleep 5
echo "API key website restrictions:"
gcloud services api-keys describe "$NAME" --project="$PROJECT_ID" \
  --format='value(restrictions.browserKeyRestrictions.allowedReferrers)' | tr ';' '\n' | sed 's/^/  /'
echo "API targets kept: $(gcloud services api-keys describe "$NAME" --project="$PROJECT_ID" --format=json \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["restrictions"].get("apiTargets", [])))')"
echo "Authorized domains:"
curl -s "${HDR[@]}" "https://identitytoolkit.googleapis.com/admin/v2/projects/$PROJECT_ID/config" \
  | python3 -c 'import json,sys; [print("  " + d) for d in json.load(sys.stdin).get("authorizedDomains", [])]'
echo "Key restrictions take up to five minutes to apply."
