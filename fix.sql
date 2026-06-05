ALTER TABLE marketplace_listings ADD COLUMN inventory_quantity INTEGER DEFAULT -1;
ALTER TABLE marketplace_listings ADD COLUMN inventory_sold INTEGER DEFAULT 0;
ALTER TABLE marketplace_listings ADD COLUMN inventory_reserved INTEGER DEFAULT 0;
ALTER TABLE marketplace_listings ADD COLUMN inventory_status VARCHAR(32) DEFAULT 'active';
ALTER TABLE marketplace_listings ADD COLUMN version_identifier VARCHAR(64) DEFAULT '1.0.0';
