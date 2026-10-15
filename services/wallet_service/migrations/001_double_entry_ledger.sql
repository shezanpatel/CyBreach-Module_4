CREATE TABLE IF NOT EXISTS wallet_ledger (
    id UUID PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    amount NUMERIC(18, 2) NOT NULL,
    reference_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user_id
    ON wallet_ledger (user_id);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_reference_id
    ON wallet_ledger (reference_id);

CREATE INDEX IF NOT EXISTS idx_wallet_ledger_created_at
    ON wallet_ledger (created_at);