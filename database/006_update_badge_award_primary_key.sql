CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE badge_award
RENAME COLUMN id TO award_id;

ALTER TABLE badge_award
ALTER COLUMN award_id DROP DEFAULT;

ALTER TABLE badge_award
ALTER COLUMN award_id TYPE VARCHAR(36)
USING award_id::text;

ALTER TABLE badge_award
ALTER COLUMN award_id SET DEFAULT gen_random_uuid()::text;