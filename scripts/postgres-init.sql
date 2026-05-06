-- Runs once when Postgres data directory is initialized.
-- Subsequent restarts skip this file.

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
