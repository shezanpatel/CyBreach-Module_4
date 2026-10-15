-- ============================================================
-- Migration 003
-- Strong Idempotency Request Fingerprinting
-- ============================================================
--
-- Adds request_hash to idempotency_keys.
--
-- The hash represents the immutable request parameters used
-- when the idempotency key was first consumed.
--
-- This prevents:
--
--   Key ABC + $50
--   Key ABC + $100
--
-- from being treated as the same request.
--
-- ============================================================


ALTER TABLE idempotency_keys
ADD COLUMN IF NOT EXISTS request_hash VARCHAR(64);


-- Existing records were created before request hashing existed.
--
-- We cannot safely reconstruct their original request payload,
-- therefore we give those historical records a deterministic
-- legacy value rather than inventing a request fingerprint.
--
-- New wallet requests will always provide a real SHA-256 hash.

UPDATE idempotency_keys
SET request_hash = encode(
    digest(
        key || ':' || user_id || ':' || endpoint,
        'sha256'
    ),
    'hex'
)
WHERE request_hash IS NULL;


ALTER TABLE idempotency_keys
ALTER COLUMN request_hash SET NOT NULL;


CREATE INDEX IF NOT EXISTS
idx_idempotency_keys_user_endpoint
ON idempotency_keys (
    user_id,
    endpoint
);