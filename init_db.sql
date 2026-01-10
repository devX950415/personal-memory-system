-- Initialize PersonalMem PostgreSQL Database
-- Note: Database 'personalmem' is already created by POSTGRES_DB environment variable

-- Create user_memories table
CREATE TABLE IF NOT EXISTS user_memories (
    user_id TEXT PRIMARY KEY,
    memories JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create index on memories JSONB for faster queries
CREATE INDEX IF NOT EXISTS idx_memories_gin ON user_memories USING GIN (memories);
