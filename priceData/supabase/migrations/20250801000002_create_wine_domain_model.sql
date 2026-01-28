-- Migration based on existing Hibernate HBM files
-- Replaces the previous wine tables with the original domain model

-- Drop existing tables if they exist
DROP TABLE IF EXISTS public.wine_reviews CASCADE;
DROP TABLE IF EXISTS public.wine_prices CASCADE;
DROP TABLE IF EXISTS public.wines CASCADE;

-- Create sequences (PostgreSQL equivalent of Hibernate sequences)
CREATE SEQUENCE IF NOT EXISTS wine_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS rating_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS ratingagency_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS offering_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS provider_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS wineoffering_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS unit_id_seq START 1;

-- Create WINE table (main wine entity)
CREATE TABLE IF NOT EXISTS public.wine (
    id BIGINT PRIMARY KEY DEFAULT nextval('wine_id_seq'),
    origin TEXT,
    vintage INTEGER,
    name TEXT,
    region TEXT,
    producer TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create RATINGAGENCY table (wine rating organizations)
CREATE TABLE IF NOT EXISTS public.ratingagency (
    id BIGINT PRIMARY KEY DEFAULT nextval('ratingagency_id_seq'),
    ratingagencyname TEXT NOT NULL,
    maxpoints DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create RATING table (wine ratings from agencies)
CREATE TABLE IF NOT EXISTS public.rating (
    id BIGINT PRIMARY KEY DEFAULT nextval('rating_id_seq'),
    wine_id BIGINT NOT NULL REFERENCES public.wine(id) ON DELETE CASCADE,
    agency_id BIGINT REFERENCES public.ratingagency(id) ON DELETE SET NULL,
    score DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create PROVIDER table (wine sellers/auction houses)
CREATE TABLE IF NOT EXISTS public.provider (
    id BIGINT PRIMARY KEY DEFAULT nextval('provider_id_seq'),
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create OFFERING table (price offerings/auctions)
CREATE TABLE IF NOT EXISTS public.offering (
    id BIGINT PRIMARY KEY DEFAULT nextval('offering_id_seq'),
    provider_id BIGINT REFERENCES public.provider(id) ON DELETE SET NULL,
    pricemin DECIMAL(10,2),
    pricemax DECIMAL(10,2),
    offeringdate DATE,
    providerofferingid TEXT NOT NULL,
    realizedprice DECIMAL(10,2),
    isohk BOOLEAN DEFAULT FALSE,
    eventidentifier TEXT,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create UNIT table (bottle sizes/units)
CREATE TABLE IF NOT EXISTS public.unit (
    id BIGINT PRIMARY KEY DEFAULT nextval('unit_id_seq'),
    deciliters DECIMAL(6,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create WINEOFFERING table (many-to-many relationship between wines and offerings)
CREATE TABLE IF NOT EXISTS public.wineoffering (
    id BIGINT PRIMARY KEY DEFAULT nextval('wineoffering_id_seq'),
    wine_id BIGINT REFERENCES public.wine(id) ON DELETE CASCADE,
    wineunit_id BIGINT REFERENCES public.unit(id) ON DELETE SET NULL,
    offering_id BIGINT REFERENCES public.offering(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_wine_name ON public.wine(name);
CREATE INDEX IF NOT EXISTS idx_wine_producer ON public.wine(producer);
CREATE INDEX IF NOT EXISTS idx_wine_region ON public.wine(region);
CREATE INDEX IF NOT EXISTS idx_wine_vintage ON public.wine(vintage);
CREATE INDEX IF NOT EXISTS idx_wine_origin ON public.wine(origin);

CREATE INDEX IF NOT EXISTS idx_rating_wine_id ON public.rating(wine_id);
CREATE INDEX IF NOT EXISTS idx_rating_agency_id ON public.rating(agency_id);
CREATE INDEX IF NOT EXISTS idx_rating_score ON public.rating(score);

CREATE INDEX IF NOT EXISTS idx_offering_provider_id ON public.offering(provider_id);
CREATE INDEX IF NOT EXISTS idx_offering_date ON public.offering(offeringdate);
CREATE INDEX IF NOT EXISTS idx_offering_provider_offering_id ON public.offering(providerofferingid);
CREATE INDEX IF NOT EXISTS idx_offering_realized_price ON public.offering(realizedprice);

CREATE INDEX IF NOT EXISTS idx_wineoffering_wine_id ON public.wineoffering(wine_id);
CREATE INDEX IF NOT EXISTS idx_wineoffering_offering_id ON public.wineoffering(offering_id);
CREATE INDEX IF NOT EXISTS idx_wineoffering_unit_id ON public.wineoffering(wineunit_id);

-- Enable Row Level Security
ALTER TABLE public.wine ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rating ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ratingagency ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.offering ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.provider ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.unit ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wineoffering ENABLE ROW LEVEL SECURITY;

-- Create policies (for now, allow all operations - adjust as needed)
CREATE POLICY "Allow all operations on wine" ON public.wine FOR ALL USING (true);
CREATE POLICY "Allow all operations on rating" ON public.rating FOR ALL USING (true);
CREATE POLICY "Allow all operations on ratingagency" ON public.ratingagency FOR ALL USING (true);
CREATE POLICY "Allow all operations on offering" ON public.offering FOR ALL USING (true);
CREATE POLICY "Allow all operations on provider" ON public.provider FOR ALL USING (true);
CREATE POLICY "Allow all operations on unit" ON public.unit FOR ALL USING (true);
CREATE POLICY "Allow all operations on wineoffering" ON public.wineoffering FOR ALL USING (true);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_wine_updated_at 
    BEFORE UPDATE ON public.wine 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rating_updated_at 
    BEFORE UPDATE ON public.rating 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ratingagency_updated_at 
    BEFORE UPDATE ON public.ratingagency 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_offering_updated_at 
    BEFORE UPDATE ON public.offering 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_provider_updated_at 
    BEFORE UPDATE ON public.provider 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_unit_updated_at 
    BEFORE UPDATE ON public.unit 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_wineoffering_updated_at 
    BEFORE UPDATE ON public.wineoffering 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some standard units (common wine bottle sizes)
INSERT INTO public.unit (deciliters) VALUES 
(3.75),   -- Half bottle (375ml)
(7.5),    -- Standard bottle (750ml)  
(15.0),   -- Magnum (1.5L)
(30.0),   -- Double Magnum (3L)
(45.0),   -- Jeroboam (4.5L)
(60.0),   -- Imperial (6L)
(90.0),   -- Salmanazar (9L)
(120.0),  -- Balthazar (12L)
(150.0),  -- Nebuchadnezzar (15L)
(180.0);  -- Melchior (18L)

-- Rating agencies will be inserted via separate migration file
