-- Add reference tables for wine regions and producers
-- These help with better parsing and data consistency

-- Wine regions reference table
CREATE TABLE IF NOT EXISTS public.wine_region (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    country VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Wine producers reference table  
CREATE TABLE IF NOT EXISTS public.wine_producer (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    country VARCHAR(50),
    website VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_wine_region_name ON public.wine_region(name);
CREATE INDEX IF NOT EXISTS idx_wine_producer_name ON public.wine_producer(name);
