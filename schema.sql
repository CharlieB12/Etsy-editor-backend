-- One-table schema for storing designs
CREATE TABLE IF NOT EXISTS designs (
  id SERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  product_id TEXT NOT NULL,
  svg TEXT NOT NULL,
  state_json TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_designs_code ON designs(code);

