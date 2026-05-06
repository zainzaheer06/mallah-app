#!/bin/bash
# D1 + post-D1 end-to-end smoke test
# Covers: auth, profile (gender/DOB), addresses (full CRUD + default invariant),
#         password change, error paths, Firebase phone OTP (if creds present)

set -e
BASE="http://localhost:8000/api/v1"
EMAIL="smoketest_$(date +%s)@example.com"
PW="supersecret123"

j() { python3 -c "import sys,json; print(json.loads(sys.stdin.read())$1)"; }
hr() { echo; echo "── $1 ──"; }

# ============================================================================
# AUTH — Email/Password
# ============================================================================

hr "1. Register"
TOKENS=$(curl -fsS -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\",\"display_name\":\"Smoke Test\"}")
echo "$TOKENS" | j ""
ACCESS=$(echo "$TOKENS"  | j "['access_token']")
REFRESH=$(echo "$TOKENS" | j "['refresh_token']")
H_AUTH="Authorization: Bearer $ACCESS"

hr "2. /me — read profile (gender + DOB should be null)"
curl -fsS "$BASE/me" -H "$H_AUTH" | j ""

# ============================================================================
# PROFILE — Patch with gender/DOB + email change + validation
# ============================================================================

hr "3. /me — patch profile (display_name, language, city)"
curl -fsS -X PATCH "$BASE/me" -H "$H_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"display_name":"Renamed","default_city":"Riyadh","language":"ar"}' | j ""

hr "4. /me — patch with gender + DOB (post-D1 fields)"
curl -fsS -X PATCH "$BASE/me" -H "$H_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"gender":"male","date_of_birth":"1990-01-01"}' | j ""

hr "5. /me — future DOB should be rejected (expect 422)"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" -X PATCH "$BASE/me" -H "$H_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"date_of_birth":"2030-01-01"}'

hr "6. /me — under-13 DOB should be rejected (expect 422)"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" -X PATCH "$BASE/me" -H "$H_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"date_of_birth":"2020-01-01"}'

hr "7. /me — change email (expect 200, is_email_verified false)"
NEW_EMAIL="changed_$(date +%s)@example.com"
curl -fsS -X PATCH "$BASE/me" -H "$H_AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$NEW_EMAIL\"}" | j ""
EMAIL="$NEW_EMAIL"  # use the changed email for subsequent tests

# ============================================================================
# ADDRESSES — Full CRUD with default invariant
# ============================================================================

hr "8. Address — create first (auto-default)"
ADDR1=$(curl -fsS -X POST "$BASE/me/addresses" -H "$H_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"label":"Home","address_line":"King Fahd Road, Bldg 5","city":"Riyadh","district":"Olaya","latitude":24.7136,"longitude":46.6753,"is_default":true}')
ADDR1_ID=$(echo "$ADDR1" | j "['id']")
echo "$ADDR1" | j ""

hr "9. Address — create second (NOT default)"
ADDR2=$(curl -fsS -X POST "$BASE/me/addresses" -H "$H_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"label":"Office","address_line":"Olaya Tower 5","city":"Riyadh","is_default":false}')
ADDR2_ID=$(echo "$ADDR2" | j "['id']")
echo "$ADDR2" | j ""

hr "10. Address — create third with is_default:true (auto-unsets first)"
ADDR3=$(curl -fsS -X POST "$BASE/me/addresses" -H "$H_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"label":"Al Wurud","address_line":"Al Wurud Apt 12","city":"Riyadh","is_default":true}')
ADDR3_ID=$(echo "$ADDR3" | j "['id']")
echo "$ADDR3" | j ""

hr "11. Address — list (only Al Wurud should be default)"
curl -fsS "$BASE/me/addresses" -H "$H_AUTH" | j ""

hr "12. Address — switch default via PATCH (Office becomes default)"
curl -fsS -X PATCH "$BASE/me/addresses/$ADDR2_ID" -H "$H_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"is_default":true}' | j ""

hr "13. Address — list again (only Office should be default)"
curl -fsS "$BASE/me/addresses" -H "$H_AUTH" | j ""

hr "14. Address — patch label (should NOT affect default)"
curl -fsS -X PATCH "$BASE/me/addresses/$ADDR2_ID" -H "$H_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"label":"Work HQ"}' | j ""

hr "15. Address — delete one (expect 204)"
curl -fsS -X DELETE "$BASE/me/addresses/$ADDR1_ID" -H "$H_AUTH" -o /dev/null -w "HTTP %{http_code}\n"

hr "16. Address — delete non-existent (expect 404)"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" -X DELETE \
  "$BASE/me/addresses/00000000-0000-0000-0000-000000000000" -H "$H_AUTH"

# ============================================================================
# PASSWORD CHANGE (post-D1 endpoint)
# ============================================================================

hr "17. Password change — wrong old password (expect 401)"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" -X POST "$BASE/me/password/change" \
  -H "$H_AUTH" -H "Content-Type: application/json" \
  -d "{\"old_password\":\"wrong_old\",\"new_password\":\"new_pw_123456\"}"

hr "18. Password change — same old/new (expect 400)"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" -X POST "$BASE/me/password/change" \
  -H "$H_AUTH" -H "Content-Type: application/json" \
  -d "{\"old_password\":\"$PW\",\"new_password\":\"$PW\"}"

hr "19. Password change — valid (expect 204)"
NEW_PW="new_pw_$(date +%s)"
curl -sS -o /dev/null -w "HTTP %{http_code}\n" -X POST "$BASE/me/password/change" \
  -H "$H_AUTH" -H "Content-Type: application/json" \
  -d "{\"old_password\":\"$PW\",\"new_password\":\"$NEW_PW\"}"

hr "20. Old password no longer works (expect 401)"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\"}"

hr "21. New password works (expect 200)"
NEW_TOKENS=$(curl -fsS -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$NEW_PW\"}")
echo "$NEW_TOKENS" | j ""
ACCESS=$(echo "$NEW_TOKENS" | j "['access_token']")
REFRESH=$(echo "$NEW_TOKENS" | j "['refresh_token']")
H_AUTH="Authorization: Bearer $ACCESS"
PW="$NEW_PW"

# ============================================================================
# AUTH — Refresh, logout, password reset
# ============================================================================

hr "22. Refresh token — exchange for new pair"
curl -fsS -X POST "$BASE/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}" | j ""

hr "23. Logout (expect 204)"
curl -fsS -X POST "$BASE/auth/logout" -H "$H_AUTH" -o /dev/null -w "HTTP %{http_code}\n"

hr "24. Password reset request — real email"
curl -fsS -X POST "$BASE/auth/password/reset-request" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\"}" | j ""

hr "25. Password reset — non-existent email (same shape, no leak)"
curl -fsS -X POST "$BASE/auth/password/reset-request" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"nobody-$(date +%s)@example.com\"}" | j ""

# ============================================================================
# ERROR PATHS
# ============================================================================

hr "26. Duplicate email → expect 409"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\"}"

hr "27. Wrong password → expect 401"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"definitely-wrong\"}"

hr "28. Missing auth header → expect 401"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" "$BASE/me"

hr "29. Bad token → expect 401"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" "$BASE/me" \
  -H "Authorization: Bearer not.a.real.token"

hr "30. Refresh token used as access → expect 401"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" "$BASE/me" \
  -H "Authorization: Bearer $REFRESH"

# ============================================================================
# FIREBASE PHONE OTP (skipped gracefully if creds not set)
# ============================================================================

hr "31. Firebase phone OTP — full flow"
WEB_API_KEY=$(grep "^FIREBASE_WEB_API_KEY" .env 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'")
if [ -z "$WEB_API_KEY" ]; then
  echo "⊘ SKIPPED — FIREBASE_WEB_API_KEY not in .env"
else
  echo "Sending OTP request via Firebase REST API..."
  SEND=$(curl -fsS -X POST \
    "https://identitytoolkit.googleapis.com/v1/accounts:sendVerificationCode?key=$WEB_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"phoneNumber":"+966501234567","recaptchaToken":"ignored"}' || echo "FAILED")
  if [ "$SEND" = "FAILED" ]; then
    echo "⊘ Firebase REST send failed (test number may not be configured)"
  else
    SESSION_INFO=$(echo "$SEND" | j "['sessionInfo']")
    echo "Confirming OTP with test code 123456..."
    CONFIRM=$(curl -fsS -X POST \
      "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPhoneNumber?key=$WEB_API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"sessionInfo\":\"$SESSION_INFO\",\"code\":\"123456\"}")
    ID_TOKEN=$(echo "$CONFIRM" | j "['idToken']")
    echo "Exchanging Firebase ID token for Mallah JWTs..."
    FB_TOKENS=$(curl -fsS -X POST "$BASE/auth/firebase" \
      -H "Content-Type: application/json" \
      -d "{\"id_token\":\"$ID_TOKEN\"}")
    echo "$FB_TOKENS" | j ""
    FB_ACCESS=$(echo "$FB_TOKENS" | j "['access_token']")

    hr "32. Firebase user — change-password should reject (expect 400)"
    curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" -X POST "$BASE/me/password/change" \
      -H "Authorization: Bearer $FB_ACCESS" \
      -H "Content-Type: application/json" \
      -d '{"old_password":"anything","new_password":"new_pw_123456"}'
  fi
fi

# ============================================================================
# SOFT DELETE (last — burns the test account)
# ============================================================================

hr "33. Soft-delete account (expect 204)"
curl -fsS -X DELETE "$BASE/me" -H "$H_AUTH" -o /dev/null -w "HTTP %{http_code}\n"

hr "34. Login with deleted account → expect 401"
curl -sS -o /dev/stdout -w "\nHTTP %{http_code}\n" -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\"}"

# ============================================================================
# HEALTH CHECKS
# ============================================================================

hr "35. /health — liveness"
curl -fsS "http://localhost:8000/health" | j ""

hr "36. /health/ready — DB + Redis readiness"
curl -fsS "http://localhost:8000/health/ready" | j ""

echo
echo "✅ D1 + post-D1 smoke test complete"
