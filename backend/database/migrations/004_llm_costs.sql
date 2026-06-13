-- LLM Costs Table for tracking Gemini usage
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS llm_costs (
    id SERIAL PRIMARY KEY,
    user_phone TEXT,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    estimated_cost DECIMAL(10, 6) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster queries by date
CREATE INDEX IF NOT EXISTS idx_llm_costs_timestamp ON llm_costs(timestamp);

-- Create index for user queries
CREATE INDEX IF NOT EXISTS idx_llm_costs_user_phone ON llm_costs(user_phone);

-- Enable RLS (Row Level Security) but allow all operations for now
ALTER TABLE llm_costs ENABLE ROW LEVEL SECURITY;

-- Policy to allow all operations (adjust for production)
CREATE POLICY "Allow all operations on llm_costs" ON llm_costs
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Grant access to authenticated and anon users
GRANT ALL ON llm_costs TO authenticated;
GRANT ALL ON llm_costs TO anon;
GRANT USAGE, SELECT ON SEQUENCE llm_costs_id_seq TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE llm_costs_id_seq TO anon;
