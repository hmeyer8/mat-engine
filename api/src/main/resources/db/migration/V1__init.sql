-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Sentinel-2 scenes metadata
CREATE TABLE IF NOT EXISTS s2_scenes (
  id SERIAL PRIMARY KEY,
  item_id TEXT UNIQUE NOT NULL,
  sensed_at TIMESTAMP WITH TIME ZONE NOT NULL,
  mgrs_tile TEXT,
  cloud_cover DOUBLE PRECISION,
  bbox geometry(Polygon, 4326),
  red_path TEXT,   -- path to clipped B04 GeoTIFF
  nir_path TEXT,   -- path to clipped B08 GeoTIFF
  ndvi_path TEXT,  -- path to processed NDVI GeoTIFF
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for spatial queries
CREATE INDEX IF NOT EXISTS idx_s2_scenes_bbox ON s2_scenes USING GIST (bbox);