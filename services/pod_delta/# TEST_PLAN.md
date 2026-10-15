# TEST_PLAN — CyBreach Arena Pod Delta Backend

Tester: Medha
Date: ____
Server: http://127.0.0.1:8000
Token claims used: `sub = "1"`, `tenant_id = "tenant_123"`

How to use: send each request from `api_requests.http`, compare the status with **Expected**, and put ✅ or ❌ in **Result**. Write anything odd in **Notes**, for example an unexpected status or an error message.

> Only the **Integration** endpoints check the JWT. Notifications, Preferences and Analytics are open, so a 201 there doesn't prove the token works. Section 6 is where the token is really tested.

## 1. Health

| ID | Request | Expected | Result | Notes |
|----|---------|----------|--------|-------|
| H-01 | `GET /` | 200 | | |
| H-02 | `GET /api/v1/health` | 200, `"status": "healthy"` | | |
| H-03 | `GET /api/v1/integration/health` | 200 (`"degraded"` is OK if Redis/Kafka aren't running) | | |
| H-04 | `GET /metrics` | 200, plain-text metrics | | |

## 2. Notifications — `/api/v1/notifications`

| ID | Request | Expected | Result | Notes |
|----|---------|----------|--------|-------|
| N-01 | `POST /` (valid body) | 201, returns `id` | ✅ | id = __2__ |
| N-02 | `POST /` with `title` missing | 422 |✅ | |
| N-03 | `POST /` with `"channel": "fax"` | 422 | ✅| |
| N-04 | `GET /` | 200, list includes N-01 |✅ | |
| N-05 | `GET /?channel=email&priority=high` | 200, only matching items |✅ | |
| N-06 | `GET /user/1` | 200, only user 1's notifications |✅ | |
| N-07 | `GET /unread` | 200 | ✅| |
| N-08 | `GET /unread/count` | 200, count ≥ 1 | ✅| |
| N-09 | `GET /stats` | 200, totals by channel/priority/status |✅ | |
| N-10 | `PUT /{id}` (change title) | 200, title updated | ✅| |
| N-11 | `PATCH /{id}/read` | 200, `is_read: true` | ✅| |
| N-12 | `PATCH /{id}/status` (e.g. `"delivered"`) | 200 | ✅| |
| N-13 | `PATCH /bulk/read` with a list of ids | 200 | ✅| |
| N-14 | `PUT /999999` (id that doesn't exist) | 404 | ✅| |
| N-15 | `DELETE /{id}` | 200 |✅ | |
| N-16 | `DELETE /{id}` again (same id) | 404 |✅ | |
| N-17 | `DELETE /bulk` with a list of ids | 200 | ✅| |

## 3. Preferences — `/api/v1/preferences`

| ID | Request | Expected | Result | Notes |
|----|---------|----------|--------|-------|
| P-01 | `POST /` for user 1 | 201 | ✅| |
| P-02 | `POST /` for user 1 again | 409 (already exists) | | |
| P-03 | `GET /1` | 200 |✅ | |
| P-04 | `GET /999999` | 404 |✅ | |
| P-05 | `PUT /1` (e.g. turn SMS off, set quiet hours) | 200, changes saved |✅ | |
| P-06 | `PUT /999999` | 404 | ✅| |
| P-07 | `user_id 0` | 422 | ✅| |
| P-08 | `invalid quiet hours` | 422 |200 |1. Preferences accept invalid values (P-08). PUT /api/v1/preferences/{user_id} saved quiet_hours_start: "25:99" and frequency: "whenever" with a 200. The schema declares both as plain str with no validation. Expected: 422. Suggested fix: validate times as HH:MM (00:00–23:59) and restrict frequency to a fixed set of values (e.g. realtime / hourly / daily / weekly).2. weekly_summary can't be changed. It's returned in every preference response (default true) but isn't accepted by POST or PUT, so users can't turn it off. | made aot changes in app/schemas/preferences.py

## 4. Analytics — `/api/v1/analytics`

| ID | Request | Expected | Result | Notes |
|----|---------|----------|--------|-------|
| A-01 | `POST /` (tenant `tenant_123`) | 201, returns `id` | | id = _1___ |
| A-01b | `POST /` (tenant `tenant_123`) | 201, returns `id` | | id = ___1_ |
| A-02 | `POST /` with invalid data (e.g. score as text) | 422 |✅ | |
| A-03 | `GET /` | 200 | ✅| |
| A-04 | `GET /?skip=0&limit=10&tenant_id=tenant_123` | 200, filtered | ✅| |
| A-05 | `GET /{id}` | 200 |✅ | |
| A-06 | `GET /999999` | 404 | ✅| |
| A-07 | `GET /tenant/tenant_123` | 200 |✅ | |
| A-08 | `GET /dashboard/tenant_123` | 200 | ✅| |
| A-09 | `GET /credit-flow/tenant_123` | 200 | ✅| |
| A-10 | `GET /engagement/tenant_123` | 200 | ✅| |
| A-11 | `GET /score/tenant_123` | 200 |✅ | |
| A-12 | `GET /score-trend/tenant_123` | 200 |✅ | |
| A-13 | `GET /report/tenant_123` | 200 |✅ | |
| A-14 | `PUT /{id}` | 200 |✅ | |
| A-15 | `DELETE /{id}` | 200 |✅ | |
| A-15b | `POST /` (tenant `tenant_123`) | 201, returns `id` |✅ | id = __1__ |
| A-16 | `POST /` (tenant `tenant_123`) | 201, returns `id` | ✅| id = __1__ |
| A-17 | `POST /` (tenant `tenant_123`) | 201, returns `id` |✅ | id = _1___ |
| A-18 | `POST /` (tenant `tenant_123`) | 201, returns `id` |✅ | id = _1___ |
| A-19 | `POST /` (tenant `tenant_123`) | 201, returns `id` | ✅| id = __1__ |

## 5. Integration — `/api/v1/integration` (JWT required)

| ID | Request | Expected | Result | Notes |
|----|---------|----------|--------|-------|
| I-01 | `GET /score/tenant_123` with valid token | 404 "Score not cached" if no score was published yet; 500 if Redis isn't running | ✅| |
| I-02 | `POST /analytics/flush/tenant_123` with valid token | 410 Gone (this is intended by the code) |✅ | |
| I-03 | `GET /metrics` | 200 | ✅| |

## 6. Security (JWT)

| ID | Request | Expected | Result | Notes |
|----|---------|----------|--------|-------|
| S-01 | `GET /integration/score/tenant_123` with **no** Authorization header | 401 "Not authenticated" |✅ | |
| S-02 | Same, with `Bearer abc123` (garbage token) | 401 "Invalid or expired token" |✅ | |
| S-03 | Same, with a token signed with a different secret | 401 | ✅| |
| S-04 | Same, with an expired token (`exp` in the past) | 401 |✅ | |
| S-05 | `GET /integration/score/tenant_999` with the `tenant_123` token | 403 "Tenant scope mismatch" |✅ | |
| S-06 | `POST /integration/analytics/flush/tenant_999` with the `tenant_123` token | 403 |✅ | |
| S-07 | Valid token, correct tenant (same as I-01) | not 401/403 | ✅| |
| S-08 | `POST /integration/analytics/flush/tenant_123` with a token that has **no `exp`** | 401 "Invalid or expired token" | ✅ | Before fix: 410 (accepted, never expires). Fixed with `require_exp: True` in security.py |
| S-09 | Same, with a token that has **no `tenant_id`** (`sub: "tenant_123"`) | 401 "Token is missing tenant_id" | ✅ | Before fix: 410 (sub used as tenant). Fixed by removing `or subject` fallback |
| S-10 | `GET /integration/score/tenant_123` with the token but **no "Bearer"** word | 401 "Not authenticated" | ✅ | |

## Summary

| Section | Total | Passed | Failed | Fixed during testing |
|---------|-------|--------|--------|----------------------|
| Health | 4 | | | |
| Notifications | 17 | 17 | 0 | 0 |
| Preferences | 8 | 8 | 0 | 1 (P-08) |
| Analytics | 21 | 21 | 0 | 1 (A-19) |
| Integration | 3 | 3 | 0 | 0 |
| Security | 10 | 10 | 0 | 2 (S-08, S-09) |

Environment: Windows, local SQLite, Redis/Kafka not running (I-01/S-07 tested auth only).

Issues found:

**Fixed**
1. **Preferences accept invalid values (P-08).** `quiet_hours_start: "25:99"` and `frequency: "whenever"` were saved with 200. Fixed in `preference_schema.py`: HH:MM pattern and allowed frequency values.
2. **Analytics accept impossible data (A-19).** active_users > total_users, negative credits, and free-text `report_month` were accepted (engagement showed 250%). Fixed in `analytics_schema.py`: non-negative fields, YYYY-MM format, active ≤ total check.
3. **Validation handler crashed with 500 on custom validators.** `exc.errors()` contained objects that couldn't be converted to JSON. Fixed in `exceptions.py` with `jsonable_encoder`.
4. **Tokens without `exp` never expired (S-08).** Fixed in `security.py` with `require_exp: True`.
5. **Missing `tenant_id` fell back to the user id (S-09).** A token with `sub: "tenant_123"` got tenant_123's access. Fixed in `security.py` by removing the fallback. Tokens now need `exp` and `tenant_id`/`tid`/`org_id`; identity-service team informed.

**Open**
6. **`delivered_at` not set (N-12).** Changing status to "delivered" leaves `delivered_at` as null.
7. **`weekly_summary` can't be changed.** Defaults to true and isn't accepted by preferences POST/PUT.
8. **Analytics PUT doesn't check active_users against the stored total_users.** Only checked when both are in the same request; needs a check in `update_analytics`.
9. **Inconsistent error format.** Analytics errors return `{"detail": ...}`; other endpoints return `{"success": false, "error": {...}}`.
10. **Silent SECRET_KEY fallback.** Without a `.env` file, the app runs with the default `your-secret-key-here` instead of failing to start.
11. **Score trend sorts `report_month` as text.** Mitigated by the YYYY-MM validation, but records created before the fix may still sort wrongly.