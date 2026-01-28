-- Create wines table for wine price data
CREATE TABLE IF NOT EXISTS public.wines (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    producer TEXT,
    vintage INTEGER,
    region TEXT,
    country TEXT,
    wine_type TEXT CHECK (wine_type IN ('red', 'white', 'rosé', 'sparkling', 'dessert', 'fortified')),
    grape_varieties TEXT[],
    price DECIMAL(10,2),
    currency TEXT DEFAULT 'EUR',
    rating DECIMAL(3,1) CHECK (rating >= 0 AND rating <= 100),
    rating_source TEXT,
    alcohol_content DECIMAL(4,2),
    volume_ml INTEGER DEFAULT 750,
    description TEXT,
    tasting_notes JSONB,
    food_pairing TEXT[],
    serving_temperature_min INTEGER,
    serving_temperature_max INTEGER,
    aging_potential_years INTEGER,
    website_url TEXT,
    image_url TEXT,
    barcode TEXT,
    availability_status TEXT CHECK (availability_status IN ('in_stock', 'out_of_stock', 'limited', 'pre_order')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create price history table
CREATE TABLE IF NOT EXISTS public.wine_prices (
    id BIGSERIAL PRIMARY KEY,
    wine_id BIGINT REFERENCES public.wines(id) ON DELETE CASCADE,
    price DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'EUR',
    retailer TEXT,
    retailer_url TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    is_promotion BOOLEAN DEFAULT FALSE,
    promotion_details TEXT
);

-- Create wine reviews table
CREATE TABLE IF NOT EXISTS public.wine_reviews (
    id BIGSERIAL PRIMARY KEY,
    wine_id BIGINT REFERENCES public.wines(id) ON DELETE CASCADE,
    reviewer_name TEXT,
    rating DECIMAL(3,1) CHECK (rating >= 0 AND rating <= 100),
    review_text TEXT,
    review_source TEXT,
    review_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_wines_producer ON public.wines(producer);
CREATE INDEX IF NOT EXISTS idx_wines_region ON public.wines(region);
CREATE INDEX IF NOT EXISTS idx_wines_vintage ON public.wines(vintage);
CREATE INDEX IF NOT EXISTS idx_wines_wine_type ON public.wines(wine_type);
CREATE INDEX IF NOT EXISTS idx_wines_price ON public.wines(price);
CREATE INDEX IF NOT EXISTS idx_wines_rating ON public.wines(rating);

CREATE INDEX IF NOT EXISTS idx_wine_prices_wine_id ON public.wine_prices(wine_id);
CREATE INDEX IF NOT EXISTS idx_wine_prices_recorded_at ON public.wine_prices(recorded_at);
CREATE INDEX IF NOT EXISTS idx_wine_prices_retailer ON public.wine_prices(retailer);

CREATE INDEX IF NOT EXISTS idx_wine_reviews_wine_id ON public.wine_reviews(wine_id);
CREATE INDEX IF NOT EXISTS idx_wine_reviews_rating ON public.wine_reviews(rating);

-- Enable Row Level Security
ALTER TABLE public.wines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wine_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wine_reviews ENABLE ROW LEVEL SECURITY;

-- Create policies (for now, allow all operations - adjust as needed)
CREATE POLICY "Allow all operations on wines" ON public.wines FOR ALL USING (true);
CREATE POLICY "Allow all operations on wine_prices" ON public.wine_prices FOR ALL USING (true);
CREATE POLICY "Allow all operations on wine_reviews" ON public.wine_reviews FOR ALL USING (true);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_wines_updated_at 
    BEFORE UPDATE ON public.wines 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
