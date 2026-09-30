ALTER TABLE users
    ALTER COLUMN email DROP NOT NULL,
    ALTER COLUMN password_hash DROP NOT NULL,
    ALTER COLUMN name DROP NOT NULL;

ALTER TABLE users
    ADD COLUMN full_name TEXT,
    ADD COLUMN avatar TEXT,
    ADD COLUMN provider TEXT,
    ADD COLUMN provider_user_id TEXT,
    ADD COLUMN login_at TEXT;

-- Pour les comptes existants, leur date de création sert de première date de connexion.
UPDATE users
SET login_at = created_at
WHERE login_at IS NULL;

ALTER TABLE users
    ALTER COLUMN login_at SET NOT NULL;

CREATE UNIQUE INDEX idx_users_provider_identity
    ON users (provider, provider_user_id)
    WHERE provider IS NOT NULL AND provider_user_id IS NOT NULL;