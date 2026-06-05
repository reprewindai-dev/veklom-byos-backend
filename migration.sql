ALTER TABLE vendors ADD COLUMN IF NOT EXISTS config_json JSON;
ALTER TABLE marketplace_listings 
  ADD COLUMN IF NOT EXISTS inventory_engine VARCHAR DEFAULT 'unlimited',
  ADD COLUMN IF NOT EXISTS reserved_quantity INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS sold_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS recurring_interval VARCHAR,
  ADD COLUMN IF NOT EXISTS revenue_share_percent INTEGER;
