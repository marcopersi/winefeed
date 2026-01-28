-- Clean, simplified wine auction schema
-- Drop all existing tables and start fresh

-- Drop existing tables in correct order (foreign keys first)
DROP TABLE IF EXISTS public.wineoffering CASCADE;
DROP TABLE IF EXISTS public.offering CASCADE;
DROP TABLE IF EXISTS public.rating CASCADE;
DROP TABLE IF EXISTS public.wine CASCADE;
DROP TABLE IF EXISTS public.provider CASCADE;
DROP TABLE IF EXISTS public.ratingagency CASCADE;
DROP TABLE IF EXISTS public.unit CASCADE;
DROP TABLE IF EXISTS public.wines CASCADE;
DROP TABLE IF EXISTS public.wine_prices CASCADE;
DROP TABLE IF EXISTS public.wine_reviews CASCADE;

-- Drop sequences
DROP SEQUENCE IF EXISTS wine_id_seq CASCADE;
DROP SEQUENCE IF EXISTS rating_id_seq CASCADE;
DROP SEQUENCE IF EXISTS ratingagency_id_seq CASCADE;
DROP SEQUENCE IF EXISTS offering_id_seq CASCADE;
DROP SEQUENCE IF EXISTS provider_id_seq CASCADE;
DROP SEQUENCE IF EXISTS wineoffering_id_seq CASCADE;
DROP SEQUENCE IF EXISTS unit_id_seq CASCADE;

-- Create simple, effective schema
CREATE TABLE IF NOT EXISTS public.provider (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    website TEXT,
    country TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.unit (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    deciliters DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.wine (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    vintage INTEGER,
    region TEXT,
    producer TEXT,
    origin TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.offering (
    id BIGSERIAL PRIMARY KEY,
    provider_id BIGINT NOT NULL REFERENCES public.provider(id),
    providerofferingid TEXT, -- Excel: providerOfferingId, PDF: Lot Number
    eventidentifier TEXT, -- Excel: eventidentifier, PDF: filename or auction ID
    offeringdate DATE, -- Excel: from sheet name, PDF: from title
    realizedprice DECIMAL(10,2), -- Final auction price
    isohk BOOLEAN DEFAULT FALSE, -- Original wooden case / Original carton
    note TEXT, -- Additional information
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.wineoffering (
    id BIGSERIAL PRIMARY KEY,
    wine_id BIGINT NOT NULL REFERENCES public.wine(id),
    offering_id BIGINT NOT NULL REFERENCES public.offering(id),
    wineunit_id BIGINT NOT NULL REFERENCES public.unit(id),
    quantity INTEGER NOT NULL DEFAULT 1, -- Number of bottles/units in this lot
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_wine_name ON public.wine(name);
CREATE INDEX IF NOT EXISTS idx_wine_vintage ON public.wine(vintage);
CREATE INDEX IF NOT EXISTS idx_wine_region ON public.wine(region);
CREATE INDEX IF NOT EXISTS idx_wine_producer ON public.wine(producer);

CREATE INDEX IF NOT EXISTS idx_offering_provider ON public.offering(provider_id);
CREATE INDEX IF NOT EXISTS idx_offering_date ON public.offering(offeringdate);
CREATE INDEX IF NOT EXISTS idx_offering_event ON public.offering(eventidentifier);
CREATE INDEX IF NOT EXISTS idx_offering_providerid ON public.offering(providerofferingid);

CREATE INDEX IF NOT EXISTS idx_wineoffering_wine ON public.wineoffering(wine_id);
CREATE INDEX IF NOT EXISTS idx_wineoffering_offering ON public.wineoffering(offering_id);
CREATE INDEX IF NOT EXISTS idx_wineoffering_unit ON public.wineoffering(wineunit_id);

-- Add updated_at trigger for wine table
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_wine_updated_at 
    BEFORE UPDATE ON public.wine 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS (can be configured later)
ALTER TABLE public.provider ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.unit ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wine ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.offering ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wineoffering ENABLE ROW LEVEL SECURITY;

-- Basic policies (allow all for now)
CREATE POLICY "Allow all on provider" ON public.provider FOR ALL USING (true);
CREATE POLICY "Allow all on unit" ON public.unit FOR ALL USING (true);
CREATE POLICY "Allow all on wine" ON public.wine FOR ALL USING (true);
CREATE POLICY "Allow all on offering" ON public.offering FOR ALL USING (true);
CREATE POLICY "Allow all on wineoffering" ON public.wineoffering FOR ALL USING (true);
